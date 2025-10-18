# inference.py
import json, re
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel, PeftConfig
import torch
import os

MODEL = "meta-llama/Llama-2-7b-chat-hf"   # base
ADAPTER = "output-llama-lora"            # where you saved PEFT adapter

# Global variables for model loading
tokenizer = None
model = None
model_loaded = False

def load_model():
    """Load the model and tokenizer only once"""
    global tokenizer, model, model_loaded
    
    if not model_loaded:
        try:
            print("Loading tokenizer and model...")
            tokenizer = AutoTokenizer.from_pretrained(MODEL, use_fast=False)
            tokenizer.pad_token = tokenizer.eos_token

            # Check if adapter exists
            if not os.path.exists(ADAPTER):
                print(f"WARNING: Adapter {ADAPTER} not found. Using base model only.")
                model = AutoModelForCausalLM.from_pretrained(
                    MODEL, 
                    device_map="auto", 
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    trust_remote_code=True
                )
            else:
                # Load base model and wrap with PEFT adapter
                base = AutoModelForCausalLM.from_pretrained(
                    MODEL, 
                    device_map="auto", 
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    trust_remote_code=True
                )
                model = PeftModel.from_pretrained(base, ADAPTER)
            
            model_loaded = True
            print("Model loaded successfully!")
            
        except Exception as e:
            print(f"Error loading model: {e}")
            model_loaded = False
            raise e

def build_prompt(text):
    instr = "Extract product attributes as JSON with keys exactly: Brand_Name, Models, Colors, Sizes/Ounce, Designs, Pattern, Costumes, Team_Names, Styles, Sets, Flavors, Pack, Albums, Movies, Formats, Edition, Platform, Digital_Copy, Refurbished, Remanufactured, Pre-Owned. Respond ONLY with a JSON object. Use null for missing fields."
    prompt = f"### Instruction:\n{instr}\n\n### Input:\n{text}\n\n### Output:\n"
    return prompt

def generate_json(text, max_new_tokens=256, temperature=0.0):
    """Generate JSON extraction from product text"""
    try:
        load_model()
        
        prompt = build_prompt(text)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        
        with torch.no_grad():
            generation_output = model.generate(
                **inputs, 
                max_new_tokens=max_new_tokens, 
                temperature=temperature, 
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id
            )
        
        decoded = tokenizer.decode(generation_output[0], skip_special_tokens=True)
        
        # Extract JSON from response
        m = re.search(r'(\{.*\})', decoded, re.S)
        if not m:
            # fallback: try from last newline
            try:
                candidate = decoded.split("### Output:")[-1].strip()
                m = re.search(r'(\{.*\})', candidate, re.S)
            except Exception:
                m = None
        
        if not m:
            return {"error": "no json found", "raw": decoded}
        
        json_str = m.group(1)
        try:
            parsed = json.loads(json_str)
            return {"json": parsed}
        except json.JSONDecodeError as e:
            return {"error": "json parse error", "raw": json_str, "decoded": decoded, "exception": str(e)}
    
    except Exception as e:
        return {"error": f"Model inference error: {str(e)}"}

def extract_with_model(product_data):
    """Extract attributes using the trained model"""
    try:
        # Build input text from product data
        text_parts = []
        
        if product_data.get('name'):
            text_parts.append(f"Title: \"{product_data['name']}\"")
        
        if product_data.get('brand'):
            text_parts.append(f"Brand: \"{product_data['brand']}\"")
        
        if product_data.get('price'):
            text_parts.append(f"Price: \"{product_data['price']}\"")
        
        if product_data.get('description'):
            text_parts.append(f"Description: \"{product_data['description']}\"")
        
        if product_data.get('sku'):
            text_parts.append(f"SKU: \"{product_data['sku']}\"")
        
        # Add size information
        if product_data.get('size_chart'):
            sizes = [s.get('size', '') for s in product_data['size_chart'] if s.get('size')]
            if sizes:
                text_parts.append(f"Sizes: \"{', '.join(sizes)}\"")
        
        # Add color information if available
        if product_data.get('colors'):
            text_parts.append(f"Colors: \"{product_data['colors']}\"")
        
        input_text = " ".join(text_parts)
        
        if not input_text.strip():
            return product_data
        
        # Use model to extract attributes
        result = generate_json(input_text)
        
        if 'json' in result:
            extracted = result['json']
            
            # Map extracted attributes back to product data
            if extracted.get('Brand_Name') and not product_data.get('brand'):
                product_data['brand'] = extracted['Brand_Name']
            
            if extracted.get('Models') and not product_data.get('model'):
                product_data['model'] = extracted['Models']
            
            if extracted.get('Colors') and not product_data.get('colors'):
                product_data['colors'] = extracted['Colors']
            
            if extracted.get('Sizes/Ounce') and not product_data.get('extracted_sizes'):
                product_data['extracted_sizes'] = extracted['Sizes/Ounce']
            
            if extracted.get('Designs'):
                product_data['designs'] = extracted['Designs']
            
            if extracted.get('Styles'):
                product_data['styles'] = extracted['Styles']
            
            if extracted.get('Pattern'):
                product_data['pattern'] = extracted['Pattern']
            
            # Store all extracted attributes
            product_data['ai_extracted'] = extracted
        
        return product_data
    
    except Exception as e:
        print(f"Error in model extraction: {str(e)}")
        return product_data

if __name__ == "__main__":
    # Example
    text = "Title: \"Acme UltraSneak 3000 - Men's Running Shoes - Blue/White - Size 10\" Description: \"Lightweight, breathable mesh, EVA sole. Price: $89.99\""
    out = generate_json(text)
    print(json.dumps(out, indent=2, ensure_ascii=False))