# train_peft.py
import os
import json
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, DataCollatorForLanguageModeling, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

MODEL = os.environ.get("MODEL", "meta-llama/Llama-2-7b-chat-hf")  # change if you have different checkpoint
OUTPUT_DIR = "output-llama-lora"
TRAIN_FILE = "data/train.jsonl"
VAL_FILE = "data/val.jsonl"
BATCH_SIZE = 1
EPOCHS = 3
LR = 2e-4
MAX_LENGTH = 1024

print("Loading dataset...")
dataset = load_dataset("json", data_files={"train":TRAIN_FILE,"validation":VAL_FILE})

print("Loading tokenizer and model...")
tokenizer = AutoTokenizer.from_pretrained(MODEL, use_fast=False)
tokenizer.pad_token = tokenizer.eos_token

# load model for kbit support if you have 4bit - otherwise normal
model = AutoModelForCausalLM.from_pretrained(MODEL, trust_remote_code=True, device_map="auto", torch_dtype="auto")

# Prepare dataset: turn instruction+input+output into single string
def format_example(ex):
    instr = ex.get("instruction","")
    inp = ex.get("input","")
    out = ex.get("output","")
    prompt = f"### Instruction:\n{instr}\n\n### Input:\n{inp}\n\n### Output:\n{out}"
    tokenized = tokenizer(prompt, truncation=True, max_length=MAX_LENGTH, padding=False)
    tokenized["labels"] = tokenized["input_ids"].copy()
    return tokenized

tokenized_train = dataset["train"].map(format_example, remove_columns=dataset["train"].column_names)
tokenized_val = dataset["validation"].map(format_example, remove_columns=dataset["validation"].column_names)

data_collator = DataCollatorForLanguageModeling(tokenizer, mlm=False)

# ---- PEFT LoRA config ----
peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],  # typical for LLaMA architectures; adjust if needed
    bias="none",
    task_type="CAUSAL_LM"
)

print("Applying PEFT/LoRA...")
model = prepare_model_for_kbit_training(model)  # safe no-op if not kbit
model = get_peft_model(model, peft_config)

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=BATCH_SIZE,
    per_device_eval_batch_size=BATCH_SIZE,
    gradient_accumulation_steps=8,
    eval_strategy="steps",
    eval_steps=200,
    logging_steps=50,
    save_strategy="steps",
    save_steps=500,
    num_train_epochs=EPOCHS,
    learning_rate=LR,
    fp16=True,
    optim="paged_adamw_32bit",
    warmup_ratio=0.03,
    save_total_limit=3,
    remove_unused_columns=False,
    report_to="none"
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_train,
    eval_dataset=tokenized_val,
    data_collator=data_collator
)

print("Starting training...")
trainer.train()
print("Saving final model & adapter...")
trainer.save_model(OUTPUT_DIR)
