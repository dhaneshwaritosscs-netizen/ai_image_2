#!/usr/bin/env python3
"""
Memory-efficient version of the Flask app without AI model
"""

from flask import Flask, render_template, request, jsonify, send_file
import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, urlparse
import time
import pandas as pd
import io
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

# Create uploads directory if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_urls_from_excel(file_path):
    """Extract URLs from Excel/CSV file"""
    try:
        # Read the file
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        urls = []
        
        # Look for URL columns (case insensitive)
        url_columns = []
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['url', 'link', 'website', 'web']):
                url_columns.append(col)
        
        # If no URL columns found, check all columns for URLs
        if not url_columns:
            for col in df.columns:
                for value in df[col].dropna():
                    if isinstance(value, str) and ('http' in value or 'www.' in value):
                        url_columns.append(col)
                        break
        
        # Extract URLs from identified columns
        for col in url_columns:
            for value in df[col].dropna():
                if isinstance(value, str):
                    # Split by common separators and clean URLs
                    potential_urls = re.split(r'[,\n\r\t]', value)
                    for url in potential_urls:
                        url = url.strip()
                        if url and ('http' in url or 'www.' in url):
                            urls.append(url)
        
        return list(set(urls))  # Remove duplicates
        
    except Exception as e:
        raise Exception(f"Error reading Excel file: {str(e)}")

def create_export_data(results, errors):
    """Create data structure for export"""
    export_data = []
    
    # Add successful results
    for result in results:
        row = {
            'URL': result.get('url', ''),
            'Product Name': result.get('name', ''),
            'Price': result.get('price', ''),
            'Brand': result.get('brand', ''),
            'SKU': result.get('sku', ''),
            'Description': result.get('description', ''),
            'Domain': result.get('domain', ''),
            'Extracted At': result.get('extracted_at', ''),
            'Status': 'Success'
        }
        
        # Add size variants if available
        if result.get('size_chart'):
            sizes = []
            for size_info in result['size_chart']:
                size = size_info.get('size', '')
                availability = size_info.get('availability', 'In Stock')
                sizes.append(f"{size} ({availability})")
            row['Sizes'] = '; '.join(sizes)
        else:
            row['Sizes'] = ''
        
        # Add materials
        if result.get('materials'):
            row['Materials'] = '; '.join(result['materials'])
        else:
            row['Materials'] = ''
        
        # Add specifications
        if result.get('specifications'):
            row['Specifications'] = '; '.join(result['specifications'])
        else:
            row['Specifications'] = ''
        
        export_data.append(row)
    
    # Add failed URLs
    for error in errors:
        row = {
            'URL': error.get('url', ''),
            'Product Name': '',
            'Price': '',
            'Brand': '',
            'SKU': '',
            'Description': '',
            'Domain': '',
            'Extracted At': '',
            'Status': 'Failed',
            'Error': error.get('error', ''),
            'Sizes': '',
            'Materials': '',
            'Specifications': ''
        }
        export_data.append(row)
    
    return export_data

def extract_product_data(url):
    """
    Extract product data from any e-commerce website (without AI model)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract product information
        product_data = {
            'url': url,
            'domain': urlparse(url).netloc,
            'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Try to extract product name from various selectors
        name_selectors = ['h1', '.product-title', '.product-name', '[data-testid="product-title"]', '.title']
        for selector in name_selectors:
            name_element = soup.select_one(selector)
            if name_element and name_element.get_text().strip():
                product_data['name'] = name_element.get_text().strip()
                break
        
        # Try to extract price from various selectors
        price_selectors = ['.price', '.product-price', '[data-testid="price"]', '.current-price', '.price-current']
        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                price_text = price_element.get_text().strip()
                if any(currency in price_text for currency in ['€', '$', '₹', '£', '¥', 'KR', 'SEK']):
                    product_data['price'] = price_text
                    break
        
        # Look for structured data (JSON-LD)
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    # Extract from Product schema
                    if data.get('@type') == 'Product':
                        if 'name' in data and 'name' not in product_data:
                            product_data['name'] = data['name']
                        if 'description' in data:
                            product_data['description'] = data['description']
                        if 'brand' in data:
                            brand = data['brand']
                            # Handle case where brand is an object
                            if isinstance(brand, dict):
                                product_data['brand'] = brand.get('name', str(brand))
                            else:
                                product_data['brand'] = str(brand)
                        if 'sku' in data:
                            product_data['sku'] = data['sku']
                        if 'offers' in data:
                            offers = data['offers']
                            if isinstance(offers, list) and len(offers) > 0:
                                offer = offers[0]
                                if 'price' in offer:
                                    product_data['price'] = f"{offer.get('priceCurrency', '')}{offer['price']}"
                        if 'image' in data:
                            if isinstance(data['image'], list):
                                product_data['images'] = data['image'][:10]  # Limit to 10 images
                            else:
                                product_data['images'] = [data['image']]
            except:
                continue
        
        # Extract images
        if 'images' not in product_data:
            images = []
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src') or img.get('data-src')
                if src:
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = urljoin(url, src)
                    if src not in images and len(images) < 10:  # Limit to 10 images
                        images.append(src)
            if images:
                product_data['images'] = images
        
        # Extract brand information
        if 'brand' not in product_data:
            brand_selectors = [
                '.brand', '.product-brand', '[data-testid="brand"]', 
                '.manufacturer', '.vendor', 'meta[property="product:brand"]',
                'meta[name="brand"]', '.company-name'
            ]
            for selector in brand_selectors:
                brand_element = soup.select_one(selector)
                if brand_element:
                    if selector.startswith('meta'):
                        product_data['brand'] = brand_element.get('content', '').strip()
                    else:
                        product_data['brand'] = brand_element.get_text().strip()
                    break
        
        # Extract SKU if not found in structured data
        if 'sku' not in product_data:
            sku_selectors = ['.sku', '.product-sku', '[data-testid="sku"]', '.product-code']
            for selector in sku_selectors:
                sku_element = soup.select_one(selector)
                if sku_element:
                    product_data['sku'] = sku_element.get_text().strip()
                    break

        # Extract description
        if 'description' not in product_data:
            desc_selectors = ['.product-description', '.description', '.product-details', 'meta[name="description"]']
            for selector in desc_selectors:
                desc_element = soup.select_one(selector)
                if desc_element:
                    if selector.startswith('meta'):
                        product_data['description'] = desc_element.get('content', '').strip()
                    else:
                        product_data['description'] = desc_element.get_text().strip()
                    break
        
        # Extract size information from various sources
        sizes = []
        
        # Extract from size selection buttons/dropdowns
        size_selectors = [
            '.size-selector button', '.size-option', '.size-button',
            'select[name*="size"] option', '.product-size', '.size-variant',
            '[data-testid*="size"]', '.variant-size', '.size-selector',
            '.size-options button', '.size-list button', '.size-grid button',
            '.size-picker button', '.size-chooser button', '.size-item',
            'button[data-size]', '.size-btn', '.size-option-btn'
        ]
        
        for selector in size_selectors:
            size_elements = soup.select(selector)
            for element in size_elements:
                size_text = element.get_text().strip()
                if size_text and size_text not in ['Size', 'Select Size', 'Choose Size', 'Size Guide']:
                    # Check if it's available or out of stock
                    availability = 'In Stock'
                    if 'disabled' in element.get('class', []) or element.get('disabled'):
                        availability = 'Out of Stock'
                    elif 'out-of-stock' in element.get('class', []):
                        availability = 'Out of Stock'
                    elif 'unavailable' in element.get('class', []):
                        availability = 'Out of Stock'
                    
                    # Check for data attributes that indicate availability
                    if element.get('data-available') == 'false':
                        availability = 'Out of Stock'
                    if element.get('data-stock') == '0':
                        availability = 'Out of Stock'
                    
                    sizes.append({
                        'size': size_text,
                        'availability': availability
                    })
        
        # Extract from SKU patterns (like "61201919\\Red\\36")
        if 'sku' in product_data and '\\' in product_data['sku']:
            sku_parts = product_data['sku'].split('\\')
            if len(sku_parts) >= 3:
                size_from_sku = sku_parts[-1]
                if size_from_sku not in [s.get('size', '') for s in sizes]:
                    sizes.append({
                        'size': size_from_sku,
                        'availability': 'In Stock'
                    })
        
        # Extract from product name patterns
        if 'name' in product_data:
            name = product_data['name']
            # Look for size patterns in the name
            size_patterns = [
                r'(?:Size|Sizes?)\s*:?\s*([A-Z0-9]+)',
                r'([A-Z0-9]+)\s*(?:Size|Sizes?)',
                r'\b([XS|S|M|L|XL|XXL|XXXL|0|2|4|6|8|10|12|14|16|18|20|22|24|26|28|30|32|34|36|38|40|42|44|46|48|50|52|54|56|58|60|62|64|66|68|70|72|74|76|78|80|82|84|86|88|90|92|94|96|98|100]+)\b'
            ]
            
            for pattern in size_patterns:
                size_match = re.search(pattern, name, re.IGNORECASE)
                if size_match:
                    size_from_name = size_match.group(1)
                    if size_from_name not in [s.get('size', '') for s in sizes]:
                        sizes.append({
                            'size': size_from_name,
                            'availability': 'In Stock'
                        })
        
        if sizes:
            product_data['size_chart'] = sizes

        # Extract materials and specifications from text
        page_text = soup.get_text()
        
        # Look for materials section
        materials_match = re.search(r'Materials:?\s*(.*?)(?=Specifications:|$)', page_text, re.IGNORECASE | re.DOTALL)
        if materials_match:
            materials_text = materials_match.group(1).strip()
            materials = [m.strip() for m in materials_text.split('-') if m.strip()]
            if materials:
                product_data['materials'] = materials

        # Look for specifications section
        specs_match = re.search(r'Specifications:?\s*(.*?)(?=Style|$)', page_text, re.IGNORECASE | re.DOTALL)
        if specs_match:
            specs_text = specs_match.group(1).strip()
            specifications = [s.strip() for s in specs_text.split('-') if s.strip()]
            if specifications:
                product_data['specifications'] = specifications

        # Extract additional metadata
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name', '').lower()
            content = meta.get('content', '')
            if name in ['keywords', 'author'] and content:
                product_data[name] = content
        
        return product_data
        
    except requests.RequestException as e:
        return {'error': f'Error fetching the webpage: {str(e)}'}
    except Exception as e:
        return {'error': f'Error parsing the webpage: {str(e)}'}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle Excel file upload and extract URLs"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            urls = extract_urls_from_excel(file_path)
            
            # Clean up uploaded file
            os.remove(file_path)
            
            if not urls:
                return jsonify({'error': 'No URLs found in the uploaded file'}), 400
            
            return jsonify({
                'success': True,
                'urls': urls,
                'count': len(urls)
            })
            
        except Exception as e:
            # Clean up uploaded file on error
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'error': str(e)}), 400
    
    return jsonify({'error': 'Invalid file type. Please upload Excel (.xlsx, .xls) or CSV files only.'}), 400

@app.route('/export', methods=['POST'])
def export_data():
    """Export extracted data as Excel file"""
    data = request.json
    results = data.get('results', [])
    errors = data.get('errors', [])
    export_format = data.get('format', 'excel')  # 'excel' or 'csv'
    
    try:
        export_data_list = create_export_data(results, errors)
        
        if not export_data_list:
            return jsonify({'error': 'No data to export'}), 400
        
        # Create DataFrame
        df = pd.DataFrame(export_data_list)
        
        # Create file in memory
        output = io.BytesIO()
        
        if export_format == 'csv':
            df.to_csv(output, index=False, encoding='utf-8')
            mimetype = 'text/csv'
            file_extension = 'csv'
        else:
            df.to_excel(output, index=False, engine='openpyxl')
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            file_extension = 'xlsx'
        
        output.seek(0)
        
        # Generate filename with timestamp
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f'extracted_data_{timestamp}.{file_extension}'
        
        return send_file(
            output,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

@app.route('/extract', methods=['POST'])
def extract():
    data = request.json
    urls = data.get('urls', [])
    single_url = data.get('url')
    
    # Handle single URL (backward compatibility)
    if single_url and not urls:
        urls = [single_url]
    
    if not urls:
        return jsonify({'error': 'URL(s) are required'}), 400
    
    # Process multiple URLs
    results = []
    errors = []
    
    for i, url in enumerate(urls):
        if not url.strip():
            continue
            
        # Add protocol if missing
        if not url.startswith(('http://', 'https://',)):
            url = 'https://' + url
        
        try:
            result = extract_product_data(url)
            if 'error' in result:
                errors.append({
                    'url': url,
                    'error': result['error'],
                    'index': i
                })
            else:
                result['url_index'] = i
                results.append(result)
        except Exception as e:
            errors.append({
                'url': url,
                'error': str(e),
                'index': i
            })
    
    return jsonify({
        'results': results,
        'errors': errors,
        'total_urls': len(urls),
        'successful': len(results),
        'failed': len(errors)
    })

if __name__ == '__main__':
    print("Starting Memory-Efficient Product Extraction Server...")
    print("AI Model: DISABLED (to avoid memory issues)")
    print("Server will run on http://localhost:5010")
    app.run(debug=True, host='0.0.0.0', port=5010)
