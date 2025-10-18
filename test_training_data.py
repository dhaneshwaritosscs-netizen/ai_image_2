#!/usr/bin/env python3
"""
Test script to verify the enhanced universal training data
"""

import json

def test_training_data():
    """Test the enhanced training data"""
    print("=" * 60)
    print("TESTING ENHANCED UNIVERSAL TRAINING DATA")
    print("=" * 60)
    
    # Load training data
    train_data = []
    with open('data/train.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                train_data.append(json.loads(line))
    
    # Load validation data
    val_data = []
    with open('data/val.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                val_data.append(json.loads(line))
    
    print(f"Training samples: {len(train_data)}")
    print(f"Validation samples: {len(val_data)}")
    print()
    
    # Analyze brands
    brands = set()
    for example in train_data + val_data:
        try:
            output = json.loads(example['output'])
            if 'Brand_Name' in output and output['Brand_Name']:
                brands.add(output['Brand_Name'])
        except:
            continue
    
    print(f"Unique brands in dataset: {len(brands)}")
    print("Brands:", sorted(brands))
    print()
    
    # Analyze color patterns
    color_patterns = set()
    for example in train_data + val_data:
        try:
            output = json.loads(example['output'])
            if 'Colors' in output and output['Colors']:
                colors = output['Colors'].split(', ')
                for color in colors:
                    color_patterns.add(color.strip())
        except:
            continue
    
    print(f"Unique color patterns: {len(color_patterns)}")
    print("Sample colors:", sorted(list(color_patterns))[:20])
    print()
    
    # Analyze size patterns
    size_patterns = set()
    for example in train_data + val_data:
        try:
            output = json.loads(example['output'])
            if 'Sizes/Ounce' in output and output['Sizes/Ounce']:
                sizes = output['Sizes/Ounce'].split(', ')
                for size in sizes:
                    size_patterns.add(size.strip())
        except:
            continue
    
    print(f"Unique size patterns: {len(size_patterns)}")
    print("Sample sizes:", sorted(list(size_patterns))[:20])
    print()
    
    # Show examples with different color naming patterns
    print("EXAMPLES WITH DIFFERENT COLOR PATTERNS:")
    print("-" * 50)
    
    color_examples = []
    for example in train_data + val_data:
        try:
            output = json.loads(example['output'])
            if 'Colors' in output and output['Colors']:
                colors = output['Colors']
                if any(word in colors.lower() for word in ['coral', 'mint', 'sage', 'heather', 'burgundy', 'teal']):
                    color_examples.append((example['input'][:100], colors))
        except:
            continue
    
    for i, (input_text, colors) in enumerate(color_examples[:5]):
        print(f"Example {i+1}:")
        print(f"  Input: {input_text}...")
        print(f"  Colors: {colors}")
        print()
    
    print("=" * 60)
    print("DATA ANALYSIS COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    test_training_data()
