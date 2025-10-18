#!/usr/bin/env python3
"""
Universal Training Script for Enhanced Color Extraction
Simplified version for better memory management
"""

import json
import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForCausalLM, 
    TrainingArguments, 
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, TaskType
import os
from datetime import datetime

def load_training_data(train_file, val_file):
    """Load training and validation data from JSONL files"""
    train_data = []
    val_data = []
    
    # Load training data
    with open(train_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                train_data.append(json.loads(line))
    
    # Load validation data
    with open(val_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                val_data.append(json.loads(line))
    
    return train_data, val_data

def format_training_example(example):
    """Format training example for the model"""
    instruction = example['instruction']
    input_text = example['input']
    output_text = example['output']
    
    # Create a formatted prompt
    prompt = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output_text}"
    return prompt

def tokenize_function(examples, tokenizer, max_length=512):
    """Tokenize the examples"""
    # Format the examples
    texts = [format_training_example(ex) for ex in examples]
    
    # Tokenize
    tokenized = tokenizer(
        texts,
        truncation=True,
        padding=True,
        max_length=max_length,
        return_tensors="pt"
    )
    
    # For causal LM, labels are the same as input_ids
    tokenized["labels"] = tokenized["input_ids"].clone()
    
    return tokenized

def main():
    print("=" * 70)
    print("UNIVERSAL COLOR EXTRACTION TRAINING - SIMPLIFIED")
    print("=" * 70)
    
    # Configuration
    model_name = "meta-llama/Llama-2-7b-chat-hf"
    output_dir = "output-universal-simple"
    train_file = "data/train.jsonl"
    val_file = "data/val.jsonl"
    
    print(f"Model: {model_name}")
    print(f"Output Directory: {output_dir}")
    print(f"Training File: {train_file}")
    print(f"Validation File: {val_file}")
    print("=" * 70)
    
    # Load data
    print("Loading dataset...")
    train_data, val_data = load_training_data(train_file, val_file)
    print(f"Training samples: {len(train_data)}")
    print(f"Validation samples: {len(val_data)}")
    
    # Show sample data
    print("\nSample training data:")
    for i, example in enumerate(train_data[:3]):
        print(f"Sample {i+1}:")
        print(f"  Input: {example['input'][:100]}...")
        print(f"  Output: {example['output'][:100]}...")
    
    # Load tokenizer
    print("\nLoading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load model with reduced memory usage
    print("Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map="auto",
        low_cpu_mem_usage=True
    )
    
    print("Model loaded successfully!")
    
    # Configure LoRA
    print("Applying PEFT/LoRA...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=8,  # Reduced rank for memory efficiency
        lora_alpha=16,
        lora_dropout=0.1,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"]
    )
    
    model = get_peft_model(model, lora_config)
    print("PEFT/LoRA applied successfully!")
    
    # Tokenize datasets
    print("Tokenizing dataset...")
    train_tokenized = tokenize_function(train_data, tokenizer)
    val_tokenized = tokenize_function(val_data, tokenizer)
    print("Dataset tokenized successfully!")
    
    # Training arguments with reduced memory usage
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=5,  # Reduced epochs
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        warmup_steps=10,
        weight_decay=0.01,
        logging_dir=f"{output_dir}/logs",
        logging_steps=1,
        save_steps=50,
        eval_steps=50,
        evaluation_strategy="steps",
        save_strategy="steps",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=True,  # Use mixed precision
        dataloader_pin_memory=False,  # Disable pin memory
        remove_unused_columns=False,
        report_to=None,  # Disable wandb/tensorboard
    )
    
    # Data collator
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )
    
    # Create trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_tokenized,
        eval_dataset=val_tokenized,
        data_collator=data_collator,
    )
    
    print("=" * 70)
    print("STARTING UNIVERSAL TRAINING...")
    print("=" * 70)
    
    try:
        # Start training
        trainer.train()
        
        # Save the final model
        trainer.save_model()
        tokenizer.save_pretrained(output_dir)
        
        print("=" * 70)
        print("TRAINING COMPLETED SUCCESSFULLY!")
        print(f"Model saved to: {output_dir}")
        print("=" * 70)
        
    except Exception as e:
        print(f"ERROR during training: {e}")
        print("Training failed, but partial model may be saved.")

if __name__ == "__main__":
    main()
