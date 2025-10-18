#!/usr/bin/env python3
"""
Enhanced training script for brand, model, and color extraction
"""

import os
import json
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, DataCollatorForLanguageModeling, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
import torch

# Configuration
MODEL = os.environ.get("MODEL", "meta-llama/Llama-2-7b-chat-hf")
OUTPUT_DIR = "output-llama-lora-enhanced"
TRAIN_FILE = "data/train.jsonl"
VAL_FILE = "data/val.jsonl"
BATCH_SIZE = 1
EPOCHS = 15  # Increased epochs for better brand/model/color extraction
LR = 3e-5   # Optimized learning rate
MAX_LENGTH = 1024

print("=" * 70)
print("ENHANCED BRAND, MODEL & COLOR EXTRACTION TRAINING")
print("=" * 70)

print(f"Model: {MODEL}")
print(f"Output Directory: {OUTPUT_DIR}")
print(f"Training File: {TRAIN_FILE}")
print(f"Validation File: {VAL_FILE}")
print(f"Epochs: {EPOCHS}")
print(f"Batch Size: {BATCH_SIZE}")
print(f"Learning Rate: {LR}")
print("=" * 70)

# Check if training files exist
if not os.path.exists(TRAIN_FILE):
    print(f"ERROR: Training file {TRAIN_FILE} not found!")
    exit(1)

if not os.path.exists(VAL_FILE):
    print(f"ERROR: Validation file {VAL_FILE} not found!")
    exit(1)

print("Loading dataset...")
try:
    dataset = load_dataset("json", data_files={"train": TRAIN_FILE, "validation": VAL_FILE})
    print(f"Training samples: {len(dataset['train'])}")
    print(f"Validation samples: {len(dataset['validation'])}")
    
    # Show sample training data
    print("\nSample training data:")
    for i, sample in enumerate(dataset['train']):
        if i < 3:  # Show first 3 samples
            print(f"Sample {i+1}:")
            print(f"  Input: {sample['input'][:150]}...")
            print(f"  Output: {sample['output'][:150]}...")
            print()
except Exception as e:
    print(f"ERROR loading dataset: {e}")
    exit(1)

print("Loading tokenizer and model...")
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL, use_fast=False)
    tokenizer.pad_token = tokenizer.eos_token
    
    # Load model with appropriate settings
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, 
        trust_remote_code=True, 
        device_map="auto", 
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
    )
    print("Model loaded successfully!")
except Exception as e:
    print(f"ERROR loading model: {e}")
    exit(1)

# Prepare dataset: turn instruction+input+output into single string
def format_example(ex):
    instr = ex.get("instruction", "")
    inp = ex.get("input", "")
    out = ex.get("output", "")
    prompt = f"### Instruction:\n{instr}\n\n### Input:\n{inp}\n\n### Output:\n{out}"
    tokenized = tokenizer(prompt, truncation=True, max_length=MAX_LENGTH, padding=False)
    tokenized["labels"] = tokenized["input_ids"].copy()
    return tokenized

print("Tokenizing dataset...")
try:
    tokenized_train = dataset["train"].map(format_example, remove_columns=dataset["train"].column_names)
    tokenized_val = dataset["validation"].map(format_example, remove_columns=dataset["validation"].column_names)
    print("Dataset tokenized successfully!")
except Exception as e:
    print(f"ERROR tokenizing dataset: {e}")
    exit(1)

data_collator = DataCollatorForLanguageModeling(tokenizer, mlm=False)

# Enhanced PEFT LoRA config for brand/model/color extraction
peft_config = LoraConfig(
    r=128,  # Increased rank for better brand/model/color extraction
    lora_alpha=256,  # Increased alpha
    lora_dropout=0.05,  # Lower dropout for better learning
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    bias="none",
    task_type="CAUSAL_LM"
)

print("Applying PEFT/LoRA...")
try:
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, peft_config)
    print("PEFT/LoRA applied successfully!")
except Exception as e:
    print(f"ERROR applying PEFT: {e}")
    exit(1)

# Enhanced training arguments for brand/model/color extraction
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=64,  # Increased for stability
    eval_strategy="steps",
    eval_steps=20,  # More frequent evaluation
    logging_steps=3,  # More frequent logging
    save_strategy="steps",
    save_steps=40,  # More frequent saves
    num_train_epochs=EPOCHS,
    learning_rate=LR,
    fp16=True,
    optim="paged_adamw_32bit",
    warmup_ratio=0.15,  # Increased warmup
    save_total_limit=8,  # Keep more checkpoints
    remove_unused_columns=False,
    report_to="none",
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    dataloader_drop_last=False,
    lr_scheduler_type="cosine",  # Cosine learning rate schedule
    weight_decay=0.005,  # Lower weight decay
    max_grad_norm=1.0,  # Gradient clipping
    dataloader_num_workers=0,
    seed=42
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train,
    eval_dataset=tokenized_val,
    data_collator=data_collator
)

print("=" * 70)
print("STARTING ENHANCED BRAND, MODEL & COLOR TRAINING...")
print("=" * 70)

try:
    trainer.train()
    print("Training completed successfully!")
except Exception as e:
    print(f"ERROR during training: {e}")
    exit(1)

print("Saving final model & adapter...")
try:
    trainer.save_model(OUTPUT_DIR)
    print(f"Model saved to {OUTPUT_DIR}")
except Exception as e:
    print(f"ERROR saving model: {e}")
    exit(1)

print("=" * 70)
print("ENHANCED BRAND, MODEL & COLOR TRAINING COMPLETED!")
print("=" * 70)
print(f"Model saved to: {OUTPUT_DIR}")
print("The model is now enhanced for brand, model, and color extraction!")
print("Test it with: python app.py")
print("=" * 70)
