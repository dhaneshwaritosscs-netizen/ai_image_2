# Enhanced Product Data Extraction System

This system extracts product information from e-commerce websites using both traditional web scraping and AI-powered extraction.

## Features

- **Web Scraping**: Extracts basic product information (name, price, brand, SKU, description, images)
- **AI Enhancement**: Uses a fine-tuned LLaMA model for better attribute extraction
- **Size Detection**: Comprehensive size extraction from various sources
- **Brand Handling**: Properly handles brand objects vs strings
- **Export Support**: Export results to Excel or CSV
- **Batch Processing**: Process multiple URLs at once

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Install additional dependencies for AI model:
```bash
pip install transformers peft torch datasets
```

## Training the AI Model

1. **Prepare Training Data**: The system includes comprehensive training data in `data/train.jsonl` and `data/val.jsonl`

2. **Train the Model**:
```bash
python train_enhanced.py
```

3. **Test the Model**:
```bash
python test_extraction.py
```

## Usage

### Running the Flask App

```bash
python app.py
```

The app will be available at `http://localhost:5010`

### API Endpoints

- `POST /extract` - Extract product data from URLs
- `POST /upload` - Upload Excel/CSV file with URLs
- `POST /export` - Export extracted data

### Example Usage

```python
import requests

# Single URL extraction
response = requests.post('http://localhost:5010/extract', 
                        json={'url': 'https://example.com/product'})

# Multiple URLs extraction
response = requests.post('http://localhost:5010/extract', 
                        json={'urls': ['https://example.com/product1', 
                                     'https://example.com/product2']})
```

## Improvements Made

### 1. Fixed Brand Extraction
- Handles brand objects vs strings properly
- Added multiple brand extraction selectors
- Fixed "[object Object]" issue

### 2. Enhanced Size Extraction
- Extracts from size selection buttons
- Handles size charts and tables
- Extracts from SKU patterns
- Detects availability status

### 3. AI Model Integration
- Fine-tuned LLaMA model for better extraction
- Comprehensive training data with real e-commerce examples
- Enhanced attribute extraction (colors, designs, styles, etc.)

### 4. Better Data Structure
- Added AI-extracted columns to exports
- Improved error handling
- Better size variant handling

## Training Data

The training data includes examples from:
- Fashion (ODD MOLLY, Zara, H&M, Levi's)
- Electronics (Apple, Samsung, Sony)
- Footwear (Nike, Adidas, CASHOTT)
- Home & Kitchen (Dyson, KitchenPro)

## Model Architecture

- **Base Model**: LLaMA-2-7B-Chat
- **Fine-tuning**: LoRA (Low-Rank Adaptation)
- **Task**: Product attribute extraction
- **Output**: Structured JSON with predefined fields

## Troubleshooting

### Common Issues

1. **Brand shows "[object Object]"**
   - Fixed in the updated code
   - Now properly handles brand objects

2. **Sizes not extracted**
   - Enhanced size extraction logic
   - Multiple extraction methods implemented

3. **AI model not working**
   - Check if model files exist in `output-llama-lora/`
   - Retrain the model if needed
   - Check GPU memory requirements

### Performance Tips

1. **GPU Memory**: The model requires significant GPU memory
2. **Batch Size**: Adjust batch size based on available memory
3. **Model Loading**: Model loads on first use (may take time)

## File Structure

```
├── app.py                 # Main Flask application
├── inference.py          # AI model inference
├── train_enhanced.py     # Enhanced training script
├── test_extraction.py    # Test script
├── data/
│   ├── train.jsonl       # Training data
│   └── val.jsonl         # Validation data
├── templates/
│   └── index.html        # Web interface
└── requirements.txt       # Dependencies
```

## Next Steps

1. **Retrain the Model**: Run `python train_enhanced.py` with the new training data
2. **Test Extraction**: Use `python test_extraction.py` to verify improvements
3. **Run the App**: Start the Flask app and test with real URLs
4. **Monitor Performance**: Check extraction quality and adjust as needed

## Support

For issues or questions:
1. Check the troubleshooting section
2. Verify all dependencies are installed
3. Ensure training data is properly formatted
4. Check GPU memory requirements for AI model
