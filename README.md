# URL Data Extractor with Excel Support

A web application that extracts product information from e-commerce websites with Excel file upload and export capabilities.

## Features

- **Manual URL Input**: Paste URLs directly in the text area
- **Excel/CSV Upload**: Upload Excel (.xlsx, .xls) or CSV files containing URLs
- **Bulk Processing**: Process multiple URLs simultaneously
- **Data Export**: Export extracted data as Excel or CSV files
- **Comprehensive Data Extraction**: Extracts product names, prices, brands, SKUs, descriptions, images, and more

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Open your browser and go to `http://localhost:5000`

## Usage

### Method 1: Manual URL Input
1. Paste URLs in the text area (one per line or separated by commas)
2. Click the send button (↑) to extract data

### Method 2: Excel/CSV Upload
1. Click the 📁 button to upload an Excel or CSV file
2. The application will automatically extract URLs from the file
3. URLs will be populated in the text area
4. Click the send button to extract data

### Export Data
After extraction is complete:
1. Click "📈 Export as Excel" to download as .xlsx file
2. Click "📄 Export as CSV" to download as .csv file

## Excel File Format

The application can read URLs from Excel/CSV files with columns containing:
- URLs
- Links
- Website addresses
- Any column containing "http" or "www."

## Extracted Data Fields

- URL
- Product Name
- Price
- Brand
- SKU
- Description
- Domain
- Extracted At
- Size Variants
- Materials
- Specifications
- Images
- Status (Success/Failed)

## Error Handling

- Invalid file types are rejected
- Failed URL extractions are logged with error messages
- All errors are included in the export file
- File upload size limit: 16MB

## Technical Details

- Built with Flask (Python web framework)
- Uses BeautifulSoup for web scraping
- Pandas for Excel/CSV processing
- OpenPyXL for Excel file handling
- Responsive web interface
