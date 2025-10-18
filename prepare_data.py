# prepare_data.py
import json, random
from pathlib import Path

input_file = Path("data/sample.jsonl")
train_out = Path("data/train.jsonl")
val_out = Path("data/val.jsonl")
random.seed(42)

lines = [l.strip() for l in input_file.read_text(encoding="utf-8").strip().splitlines() if l.strip()]
random.shuffle(lines)
n = len(lines)
val_n = max(1, int(0.1 * n))

train_lines = lines[val_n:]
val_lines = lines[:val_n]

train_out.write_text("\n".join(train_lines), encoding="utf-8")
val_out.write_text("\n".join(val_lines), encoding="utf-8")
print(f"Total {n} -> train {len(train_lines)} val {len(val_lines)}")
