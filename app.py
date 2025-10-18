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

# Import the AI model for enhanced extraction
try:
    from inference import extract_with_model
    AI_MODEL_AVAILABLE = True
    print("AI model available!")
except ImportError as e:
    print(f"AI model not available: {e}")
    AI_MODEL_AVAILABLE = False

# Set to False to disable AI model and use only web scraping
USE_AI_MODEL = False  # Change to True if you want to use AI model

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
        if result.get('size_variants'):
            sizes = []
            for variant in result['size_variants']:
                sizes.append(f"{variant['size']} - {variant['price']} ({variant['availability']})")
            row['Size Variants'] = '; '.join(sizes)
        elif result.get('size_chart'):
            sizes = []
            for size_info in result['size_chart']:
                sizes.append(f"{size_info['size']} ({size_info['availability']})")
            row['Size Variants'] = '; '.join(sizes)
        else:
            row['Size Variants'] = ''
        
        # Add colors
        if result.get('colors'):
            row['Colors'] = '; '.join(result['colors'])
        else:
            row['Colors'] = ''
        
        # Add specifications
        if result.get('specifications'):
            row['Specifications'] = '; '.join(result['specifications'])
        else:
            row['Specifications'] = ''
        
        # Add AI-extracted attributes
        if result.get('ai_extracted'):
            ai_data = result['ai_extracted']
            row['AI Brand'] = ai_data.get('Brand_Name', '')
            row['AI Model'] = ai_data.get('Models', '')
            row['AI Colors'] = ai_data.get('Colors', '')
            row['AI Sizes'] = ai_data.get('Sizes/Ounce', '')
            row['AI Designs'] = ai_data.get('Designs', '')
            row['AI Styles'] = ai_data.get('Styles', '')
            row['AI Pattern'] = ai_data.get('Pattern', '')
        else:
            row['AI Brand'] = ''
            row['AI Model'] = ''
            row['AI Colors'] = ''
            row['AI Sizes'] = ''
            row['AI Designs'] = ''
            row['AI Styles'] = ''
            row['AI Pattern'] = ''
        
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
            'Size Variants': '',
            'Colors': '',
            'Materials': '',
            'Specifications': '',
            'AI Brand': '',
            'AI Model': '',
            'AI Colors': '',
            'AI Sizes': '',
            'AI Designs': '',
            'AI Styles': '',
            'AI Pattern': ''
        }
        export_data.append(row)
    
    return export_data

def extract_product_data(url):
    """
    Extract product data from any e-commerce website
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
        
        # If no title found, try to get the first non-empty H1 (handles cases where first H1 is empty)
        if 'name' not in product_data:
            h1_elements = soup.find_all('h1')
            for h1 in h1_elements:
                if h1.get_text().strip():
                    product_data['name'] = h1.get_text().strip()
                break
        
        # Try to extract price from various selectors
        price_selectors = ['.price', '.product-price', '[data-testid="price"]', '.current-price', '.price-current']
        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                price_text = price_element.get_text().strip()
                if any(currency in price_text for currency in ['€', '$', '₹', '£', '¥']):
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
                        if 'gtin13' in data:
                            product_data['gtin13'] = data['gtin13']
                        if 'offers' in data:
                            offers = data['offers']
                            if isinstance(offers, list) and len(offers) > 0:
                                offer = offers[0]
                                if 'price' in offer:
                                    product_data['price'] = f"{offer.get('priceCurrency', '')}{offer['price']}"
                                
                                # Extract size variants from offers
                                size_variants = []
                                for offer_item in offers:
                                    if isinstance(offer_item, dict) and 'sku' in offer_item:
                                        sku = offer_item['sku']
                                        if '\\' in sku:
                                            size = sku.split('\\')[-1]
                                            availability = offer_item.get('availability', '')
                                            price = offer_item.get('price', 0)
                                            currency = offer_item.get('priceCurrency', '€')
                                            
                                            size_variants.append({
                                                'size': size,
                                                'price': f"{currency}{price}",
                                                'availability': 'In Stock' if 'InStock' in availability else 'Out of Stock',
                                                'sku': sku
                                            })
                                
                                if size_variants:
                                    product_data['size_variants'] = size_variants
                                    
                            elif isinstance(offers, dict) and 'price' in offers:
                                product_data['price'] = f"{offers.get('priceCurrency', '')}{offers['price']}"
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
        
        # Enhanced brand extraction
        if 'brand' in product_data:
            brand_value = product_data['brand']
            if isinstance(brand_value, dict):
                product_data['brand'] = brand_value.get('name', '')
            else:
                product_data['brand'] = str(brand_value)
        
        if 'brand' not in product_data or not product_data['brand']:
            brand_selectors = [
                '.brand', '.product-brand', '[data-testid="brand"]', 
                '.manufacturer', '.vendor', 'meta[property="product:brand"]',
                'meta[name="brand"]', '.company-name', '[itemprop="brand"]',
                '.brand-name', '[data-brand]', '.product-manufacturer'
            ]
            for selector in brand_selectors:
                brand_element = soup.select_one(selector)
                if brand_element:
                    if selector.startswith('meta'):
                        product_data['brand'] = brand_element.get('content', '').strip()
                    else:
                        product_data['brand'] = brand_element.get_text().strip()
                    break
            
            # Try title parsing for brand if still not found
            if 'brand' not in product_data and 'name' in product_data:
                title = product_data['name']
                # Common brand patterns in titles
                brand_patterns = [
                    r'^([A-Z][a-zA-Z&\'\.\s]+?)\s+',  # Brand at start
                    r'by\s+([A-Z][a-zA-Z&\'\.\s]+?)(?:\s|$)',  # "by Brand"
                    r'from\s+([A-Z][a-zA-Z&\'\.\s]+?)(?:\s|$)',  # "from Brand"
                ]
                for pattern in brand_patterns:
                    match = re.search(pattern, title, re.IGNORECASE)
                    if match:
                        potential_brand = match.group(1).strip()
                        # Validate it's not a common word
                        if len(potential_brand) > 2 and potential_brand.lower() not in ['the', 'and', 'for', 'with', 'new', 'best']:
                            product_data['brand'] = potential_brand
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
        
        # Extract from size chart table
        size_table = soup.find('table')
        if size_table:
            rows = size_table.find_all('tr')
            for row in rows[1:]:  # Skip header row
                cells = row.find_all('td')
                if len(cells) >= 2:
                    size_info = {
                        'size': cells[0].get_text().strip(),
                        'foot_length_cm': cells[1].get_text().strip()
                    }
                    sizes.append(size_info)
        
        # Extract from size selection buttons/dropdowns - Enhanced selectors
        size_selectors = [
            # Common size selectors
            '.size-selector button', '.size-option', '.size-button',
            'select[name*="size"] option', '.product-size', '.size-variant',
            '[data-testid*="size"]', '.variant-size', '.size-selector',
            '.size-options button', '.size-list button', '.size-grid button',
            '.size-picker button', '.size-chooser button', '.size-item',
            'button[data-size]', '.size-btn', '.size-option-btn',
            
            # Additional selectors for different websites
            '.size-select', '.size-dropdown', '.size-chooser',
            '.product-variant', '.variant-selector', '.size-list',
            '.size-grid', '.size-options', '.size-picker',
            '.size-selector-item', '.size-item-button', '.size-choice',
            '.size-selector-option', '.size-selector-item',
            
            # Data attributes
            '[data-size]', '[data-variant]', '[data-option]',
            '[data-value*="size"]', '[data-name*="size"]',
            
            # Class-based selectors
            '.size', '.sizes', '.size-option', '.size-choice',
            '.variant', '.variants', '.option', '.options',
            
            # Specific e-commerce platforms
            '.swatch-option', '.swatch', '.swatch-element',
            '.product-options', '.product-option', '.option-value',
            '.attribute-option', '.attribute-options',
            
            # Generic selectors
            'button[class*="size"]', 'div[class*="size"]',
            'span[class*="size"]', 'a[class*="size"]',
            'li[class*="size"]', 'option[class*="size"]'
        ]
        
        for selector in size_selectors:
            size_elements = soup.select(selector)
            for element in size_elements:
                size_text = element.get_text().strip()
                
                # Skip common non-size text
                skip_texts = [
                    'Size', 'Select Size', 'Choose Size', 'Size Guide', 
                    'Size Chart', 'Size Information', 'Size Range',
                    'Available Sizes', 'Size Options', 'Size Selection',
                    'Please select', 'Select', 'Choose', 'Pick',
                    'Size:', 'Sizes:', 'Available:', 'Options:',
                    'Size Guide', 'Size Chart', 'Measurements',
                    'Fit', 'Fitting', 'Fit Guide', 'Size Help',
                    # Price-related terms
                    'Price', 'Cost', 'kr', '€', '$', '£', '¥', '₹',
                    'USD', 'EUR', 'GBP', 'CAD', 'AUD',
                    'Add to cart', 'Add to bag', 'Buy now',
                    'In stock', 'Out of stock', 'Available',
                    'Quantity', 'Qty', 'Amount'
                ]
                
                if size_text and size_text not in skip_texts:
                    # Clean the size text
                    size_text = re.sub(r'[^\w\s\-\.\/]', '', size_text).strip()
                    
                    # Check if it looks like a size (contains common size patterns)
                    size_patterns = [
                        r'\b(XS|S|M|L|XL|XXL|XXXL)\b',  # Letter sizes
                        r'\b(\d+\/\d+)\b',  # Range sizes like 33/34, 35/36
                        r'\b(\d+-\d+)\b',  # Range sizes like 33-34, 35-36
                        r'\b(\d+\.\d+\/\d+\.\d+)\b',  # Decimal ranges like 7.5/8.5
                        r'\b(\d+\.\d+-\d+\.\d+)\b',  # Decimal ranges like 7.5-8.5
                        r'\b(\d+[A-Z]?)\b',  # Numeric with optional letter (but not currency)
                        r'\b([A-Z]\d+)\b',  # Letter followed by number
                        r'\b(\d+[A-Z]+\d*)\b'  # Complex patterns
                    ]
                    
                    # Skip currency patterns
                    currency_patterns = [
                        r'\d+\s*(kr|€|\$|£|¥|₹|USD|EUR|GBP)',  # Currency patterns
                        r'(kr|€|\$|£|¥|₹|USD|EUR|GBP)\s*\d+',  # Currency patterns
                        r'\d+\.\d+\s*(kr|€|\$|£|¥|₹|USD|EUR|GBP)',  # Decimal currency
                        r'(kr|€|\$|£|¥|₹|USD|EUR|GBP)\s*\d+\.\d+'  # Decimal currency
                    ]
                    
                    is_currency = False
                    for pattern in currency_patterns:
                        if re.search(pattern, size_text, re.IGNORECASE):
                            is_currency = True
                            break
                    
                    is_valid_size = False
                    if not is_currency:  # Only check size patterns if not currency
                        for pattern in size_patterns:
                            if re.search(pattern, size_text, re.IGNORECASE):
                                is_valid_size = True
                                break
                    
                    if is_valid_size and len(size_text) <= 15:  # Reasonable size length
                        # Additional validation to prevent fake sizes
                        # Skip if it looks like a price, date, or other non-size data
                        fake_patterns = [
                            r'^\d{4}$',  # Years like 2024
                            r'^\d{1,2}\/\d{1,2}\/\d{4}$',  # Dates like 12/25/2024
                            r'^\d+\.\d{2}$',  # Prices like 29.99
                            r'^\d+%$',  # Percentages like 50%
                            r'^\d+px$',  # CSS values like 100px
                            r'^\d+cm$',  # Measurements like 10cm
                            r'^\d+kg$',  # Weights like 2kg
                            r'^\d+ml$',  # Volumes like 500ml
                        ]
                        
                        is_fake_size = False
                        for pattern in fake_patterns:
                            if re.search(pattern, size_text, re.IGNORECASE):
                                is_fake_size = True
                                break
                        
                        # Skip if it's a fake size
                        if is_fake_size:
                            continue
                        
                        # Check if it's available or out of stock
                        availability = 'In Stock'
                        
                        # Check class names for availability
                        class_names = ' '.join(element.get('class', []))
                        if any(word in class_names.lower() for word in ['disabled', 'unavailable', 'out-of-stock', 'sold-out']):
                            availability = 'Out of Stock'
                        
                        # Check element attributes
                        if element.get('disabled') or element.get('aria-disabled') == 'true':
                            availability = 'Out of Stock'
                        
                        # Check for data attributes that indicate availability
                        if element.get('data-available') == 'false':
                            availability = 'Out of Stock'
                        if element.get('data-stock') == '0':
                            availability = 'Out of Stock'
                        if element.get('data-in-stock') == 'false':
                            availability = 'Out of Stock'
                        
                        # Check if element is clickable (not disabled)
                        if element.name == 'button' and 'disabled' in element.get('class', []):
                            availability = 'Out of Stock'
                        
                        # Only add if not already present
                        if size_text not in [s.get('size', '') for s in sizes]:
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
        
        # Extract from page text content (look for size information in text)
        page_text = soup.get_text()
        
        # Look for size information in text patterns
        text_size_patterns = [
            r'(?:Available Sizes?|Size Options?|Size Range|Sizes? Available)\s*:?\s*([A-Z0-9\s,\.\-\/]+)',
            r'(?:Size|Sizes?)\s*:?\s*([A-Z0-9\s,\.\-\/]+)',
            r'(?:Available in|Comes in)\s*:?\s*([A-Z0-9\s,\.\-\/]+)',
            r'(?:Size Chart|Size Guide)\s*:?\s*([A-Z0-9\s,\.\-\/]+)',
            r'(?:Men\'s|Women\'s|Kids\')\s*Sizes?\s*:?\s*([A-Z0-9\s,\.\-\/]+)',
            r'(?:US|EU|UK)\s*Sizes?\s*:?\s*([A-Z0-9\s,\.\-\/]+)',
            r'(?:Select size|Size Selection)\s*:?\s*([A-Z0-9\s,\.\-\/]+)',
            r'(?:Size Options|Size Range)\s*:?\s*([A-Z0-9\s,\.\-\/]+)'
        ]
        
        for pattern in text_size_patterns:
            text_match = re.search(pattern, page_text, re.IGNORECASE)
            if text_match:
                size_text = text_match.group(1).strip()
                # Split by common separators and clean
                size_list = re.split(r'[,;|\n\r]', size_text)
                for size_item in size_list:
                    size_item = size_item.strip()
                    if size_item and len(size_item) <= 15:  # Increased length for range sizes
                        # Check if it looks like a valid size
                        if re.search(r'\b(XS|S|M|L|XL|XXL|\d+(?:\.\d+)?|\d+\/\d+|\d+-\d+)\b', size_item, re.IGNORECASE):
                            if size_item not in [s.get('size', '') for s in sizes]:
                                sizes.append({
                                    'size': size_item,
                                    'availability': 'In Stock'
                                })
        
        # Extract from meta tags and structured data
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name', '').lower()
            content = meta.get('content', '')
            if 'size' in name and content:
                # Extract sizes from meta content
                size_list = re.split(r'[,;|\s]', content)
                for size_item in size_list:
                    size_item = size_item.strip()
                    if size_item and re.search(r'\b(XS|S|M|L|XL|XXL|\d+(?:\.\d+)?|\d+\/\d+|\d+-\d+)\b', size_item, re.IGNORECASE):
                        if size_item not in [s.get('size', '') for s in sizes]:
                            sizes.append({
                                'size': size_item,
                                'availability': 'In Stock'
                            })
        
        # Extract from structured data offers
        if 'size_variants' in product_data:
            for variant in product_data['size_variants']:
                if variant.get('size') not in [s.get('size', '') for s in sizes]:
                    sizes.append({
                        'size': variant['size'],
                        'availability': variant.get('availability', 'In Stock')
                    })
        
        # Extract from JavaScript data (Shopify variants) - Only if no sizes found yet
        if not sizes:
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string and ('variants' in script.string or 'productVariants' in script.string):
                    script_content = script.string
                    
                    # Look for Shopify variant data
                    variant_patterns = [
                        r'var\s+variants\s*=\s*(\[.*?\]);',
                        r'var\s+productVariants\s*=\s*(\[.*?\]);',
                        r'variants:\s*(\[.*?\])',
                        r'productVariants:\s*(\[.*?\])'
                    ]
                    
                    for pattern in variant_patterns:
                        matches = re.findall(pattern, script_content, re.DOTALL)
                        for match in matches:
                            try:
                                # Parse the JSON-like data
                                variants_data = json.loads(match)
                                for variant in variants_data:
                                    if isinstance(variant, dict):
                                        # Extract size from title or options
                                        title = variant.get('title', '')
                                        options = variant.get('options', [])
                                        available = variant.get('available', True)
                                        
                                        # Look for size in title (e.g., "LIGHT CHALK / XS")
                                        if '/' in title:
                                            size_part = title.split('/')[-1].strip()
                                            if size_part in ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']:
                                                if size_part not in [s.get('size', '') for s in sizes]:
                                                    sizes.append({
                                                        'size': size_part,
                                                        'availability': 'In Stock' if available else 'Out of Stock'
                                                    })
                                        
                                        # Look for size in options array
                                        for option in options:
                                            if option in ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']:
                                                if option not in [s.get('size', '') for s in sizes]:
                                                    sizes.append({
                                                        'size': option,
                                                        'availability': 'In Stock' if available else 'Out of Stock'
                                                    })
                            except (json.JSONDecodeError, ValueError):
                                continue
        
        # Extract from select options (like ODD MOLLY) - Only if no sizes found yet
        if not sizes:
            select_elements = soup.find_all('select')
            for select in select_elements:
                options = select.find_all('option')
                for option in options:
                    option_text = option.get_text().strip()
                    if option_text and '/' in option_text:
                        # Extract size from option text like "LIGHT CHALK / XS"
                        size_part = option_text.split('/')[-1].strip()
                        if size_part in ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']:
                            if size_part not in [s.get('size', '') for s in sizes]:
                                sizes.append({
                                    'size': size_part,
                                    'availability': 'In Stock'
                                })
        
        # Final deduplication and validation
        if sizes:
            # Remove duplicates and validate sizes
            unique_sizes = []
            seen_sizes = set()
            
            for size_info in sizes:
                size = size_info['size']
                if size not in seen_sizes and size.strip():
                    # Additional validation for common fake sizes
                    if not re.match(r'^(2024|2025|\d+\.\d{2}|\d+%|\d+px|\d+cm|\d+kg|\d+ml)$', size, re.IGNORECASE):
                        seen_sizes.add(size)
                        unique_sizes.append(size_info)
            
            if unique_sizes:
                product_data['size_chart'] = unique_sizes

        # Enhanced color extraction
        colors = []
        
        # Extract from structured data first
        if 'color' in product_data:
            color_value = product_data['color']
            if isinstance(color_value, list):
                colors.extend(color_value)
            else:
                colors.append(str(color_value))
        
        # Extract from meta tags
        color_meta = soup.find('meta', {'property': 'product:color'}) or soup.find('meta', {'name': 'color'})
        if color_meta:
            color_content = color_meta.get('content', '').strip()
            if color_content and color_content not in colors:
                colors.append(color_content)
        
        # Extract from color selectors
        color_selectors = [
            '.color', '.product-color', '.color-option', '.color-variant',
            '[data-color]', '.color-name', '.color-value', '.swatch-color',
            '.color-swatch', '.color-picker', '.color-selector', '.available-colors',
            '[itemprop="color"]', '.product-colors', '.color-list'
        ]
        
        for selector in color_selectors:
            color_elements = soup.select(selector)
            for element in color_elements:
                color_text = element.get_text().strip()
                if color_text and len(color_text) <= 50:  # Reasonable color name length
                    # Clean color text
                    color_text = re.sub(r'[^\w\s\-\.\/]', '', color_text).strip()
                    if color_text and color_text not in colors:
                        colors.append(color_text)
        
        # Extract from page text patterns - enhanced for better color detection
        page_text = soup.get_text()
        color_patterns = [
            r'(?:Available Colors?|Color Options?|Colors? Available)\s*:?\s*([A-Za-z\s,\.\-\/]+)',
            r'(?:Color|Colors?)\s*:?\s*([A-Za-z\s,\.\-\/]+)',
            r'(?:Available in|Comes in)\s*:?\s*([A-Za-z\s,\.\-\/]+)',
            r'(?:Color Selection|Color Range)\s*:?\s*([A-Za-z\s,\.\-\/]+)',
            r'(?:Colour|Kleur)\s*:?\s*([A-Za-z\s,\.\-\/]+)',  # Dutch/UK spelling
            r'(?:Color Variants?|Color Options?)\s*:?\s*([A-Za-z\s,\.\-\/]+)',  # Enhanced patterns
            r'(?:Choose Color|Select Color|Pick Color)\s*:?\s*([A-Za-z\s,\.\-\/]+)',
            r'(\w+\s+(?:blue|red|green|yellow|black|white|gray|grey|pink|purple|orange|brown|navy|beige|silver|gold|tan|cream|ivory|maroon|burgundy|turquoise|teal|olive|lime|mint|coral|salmon|peach|rose|lavender|violet|indigo|cyan|magenta|amber|copper|bronze|platinum|raven|midnight|charcoal|ebony|jet|onyx|obsidian|coal|ink|shadow))',  # Enhanced color patterns
            r'([A-Z][A-Z\s]+(?:CHALK|MINT|SAGE|STONE|SAND|PEARL|CREAM|IVORY|CHAMPAGNE|COPPER|BRONZE|ROSE|CORAL|SALMON|PEACH|LAVENDER|VIOLET|INDIGO|CYAN|MAGENTA|AMBER|RAVEN|MIDNIGHT|CHARCOAL|EBONY|JET|ONYX|OBSIDIAN|COAL|INK|SHADOW))',  # Enhanced specific color names
            r'(\b(?:soft|light|dark|deep|bright|vivid|pale|rich|warm|cool|neutral|pastel|metallic|matte|glossy|satin|pearl|champagne|rose|gold|silver|bronze|copper|platinum)\s+(?:blue|red|green|yellow|black|white|gray|grey|pink|purple|orange|brown|navy|beige|tan|cream|ivory|maroon|burgundy|turquoise|teal|olive|lime|mint|coral|salmon|peach|rose|lavender|violet|indigo|cyan|magenta|amber))',  # Descriptive colors
        ]
        
        for pattern in color_patterns:
            text_match = re.search(pattern, page_text, re.IGNORECASE)
            if text_match:
                color_text = text_match.group(1).strip()
                # Split by common separators and clean
                color_list = re.split(r'[,;|\n\r]', color_text)
                for color_item in color_list:
                    color_item = color_item.strip()
                    if color_item and len(color_item) <= 30 and color_item not in colors:
                        # Additional validation for color patterns
                        if (re.search(r'\b(blue|red|green|yellow|black|white|gray|grey|pink|purple|orange|brown|navy|beige|silver|gold|tan|cream|ivory|maroon|burgundy|turquoise|teal|olive|lime|mint|coral|salmon|peach|rose|lavender|violet|indigo|cyan|magenta|amber|copper|bronze|platinum|chalk|sage|stone|sand|pearl|champagne)\b', color_item, re.IGNORECASE) or
                            re.search(r'\b[A-Z][A-Z\s]*(?:CHALK|MINT|SAGE|STONE|SAND|PEARL|CREAM|IVORY|CHAMPAGNE|COPPER|BRONZE|ROSE|CORAL|SALMON|PEACH|LAVENDER|VIOLET|INDIGO|CYAN|MAGENTA|AMBER)\b', color_item)):
                            colors.append(color_item)
        
        # Extract from product title and SKU - enhanced for better color detection
        if 'name' in product_data:
            title = product_data['name']
            
            # Look for color patterns in title like "Cup Slide-Raven" or "Antony - soft blue"
            title_color_patterns = [
                r'-\s*([a-z\s]+(?:blue|red|green|yellow|black|white|gray|grey|pink|purple|orange|brown|navy|beige|silver|gold|tan|cream|ivory|maroon|burgundy|turquoise|teal|olive|lime|mint|coral|salmon|peach|rose|lavender|violet|indigo|cyan|magenta|amber|copper|bronze|platinum|chalk|sage|stone|sand|pearl|champagne|raven|midnight|charcoal|ebony|jet|onyx|obsidian|coal|ink|shadow|dark|light|bright|deep|soft|vivid|pale|rich|warm|cool|neutral|pastel|metallic|matte|glossy|satin))',
                r'([a-z\s]+(?:blue|red|green|yellow|black|white|gray|grey|pink|purple|orange|brown|navy|beige|silver|gold|tan|cream|ivory|maroon|burgundy|turquoise|teal|olive|lime|mint|coral|salmon|peach|rose|lavender|violet|indigo|cyan|magenta|amber|copper|bronze|platinum|chalk|sage|stone|sand|pearl|champagne|raven|midnight|charcoal|ebony|jet|onyx|obsidian|coal|ink|shadow|dark|light|bright|deep|soft|vivid|pale|rich|warm|cool|neutral|pastel|metallic|matte|glossy|satin))',
                r'([A-Z][A-Z\s]*(?:CHALK|MINT|SAGE|STONE|SAND|PEARL|CREAM|IVORY|CHAMPAGNE|COPPER|BRONZE|ROSE|CORAL|SALMON|PEACH|LAVENDER|VIOLET|INDIGO|CYAN|MAGENTA|AMBER|RAVEN|MIDNIGHT|CHARCOAL|EBONY|JET|ONYX|OBSIDIAN|COAL|INK|SHADOW|DARK|LIGHT|BRIGHT|DEEP|SOFT|VIVID|PALE|RICH|WARM|COOL|NEUTRAL|PASTEL|METALLIC|MATTE|GLOSSY|SATIN))',
                # Specific color name patterns
                r'\b(raven|midnight|charcoal|ebony|jet|onyx|obsidian|coal|ink|shadow|crimson|scarlet|burgundy|maroon|navy|royal|sky|ocean|forest|emerald|lime|mint|sage|olive|khaki|camel|tan|beige|cream|ivory|pearl|champagne|rose|blush|coral|salmon|peach|apricot|amber|honey|gold|bronze|copper|silver|platinum|gunmetal|steel)\b',
            ]
            
            for pattern in title_color_patterns:
                match = re.search(pattern, title, re.IGNORECASE)
                if match:
                    # Use group(1) for patterns with capture groups, group(0) for patterns without
                    if match.groups():
                        color_from_title = match.group(1).strip()
                    else:
                        color_from_title = match.group(0).strip()
                    if color_from_title and color_from_title not in colors:
                        # Translate specific color names to standard colors
                        color_translations = {
                            'raven': 'Black', 'midnight': 'Black', 'charcoal': 'Dark Gray', 'ebony': 'Black',
                            'jet': 'Black', 'onyx': 'Black', 'obsidian': 'Black', 'coal': 'Black',
                            'ink': 'Black', 'shadow': 'Dark Gray', 'crimson': 'Red', 'scarlet': 'Red',
                            'burgundy': 'Dark Red', 'maroon': 'Dark Red', 'navy': 'Dark Blue',
                            'royal': 'Blue', 'sky': 'Light Blue', 'ocean': 'Blue', 'forest': 'Dark Green',
                            'emerald': 'Green', 'lime': 'Light Green', 'mint': 'Light Green',
                            'sage': 'Gray-Green', 'olive': 'Olive Green', 'khaki': 'Khaki',
                            'camel': 'Tan', 'tan': 'Tan', 'beige': 'Beige', 'cream': 'Cream',
                            'ivory': 'Ivory', 'pearl': 'Pearl', 'champagne': 'Champagne',
                            'rose': 'Pink', 'blush': 'Light Pink', 'coral': 'Coral',
                            'salmon': 'Salmon', 'peach': 'Peach', 'apricot': 'Orange',
                            'amber': 'Amber', 'honey': 'Golden', 'gold': 'Gold',
                            'bronze': 'Bronze', 'copper': 'Copper', 'silver': 'Silver',
                            'platinum': 'Platinum', 'gunmetal': 'Dark Gray', 'steel': 'Gray'
                        }
                        
                        # Check if we need to translate
                        color_lower = color_from_title.lower().strip()
                        if color_lower in color_translations:
                            translated_color = color_translations[color_lower]
                            colors.append(translated_color)
                        else:
                            colors.append(color_from_title)
        
        # Extract from SKU if available
        if 'sku' in product_data:
            sku = product_data['sku']
            # Look for color patterns in SKU like "4147526-INDIGO_BLUE"
            sku_color_patterns = [
                r'-([A-Z_]+(?:BLUE|RED|GREEN|YELLOW|BLACK|WHITE|GRAY|GREY|PINK|PURPLE|ORANGE|BROWN|NAVY|BEIGE|SILVER|GOLD|TAN|CREAM|IVORY|MAROON|BURGUNDY|TURQUOISE|TEAL|OLIVE|LIME|MINT|CORAL|SALMON|PEACH|ROSE|LAVENDER|VIOLET|INDIGO|CYAN|MAGENTA|AMBER|COPPER|BRONZE|PLATINUM|CHALK|SAGE|STONE|SAND|PEARL|CHAMPAGNE))',
                r'_([A-Z_]+(?:BLUE|RED|GREEN|YELLOW|BLACK|WHITE|GRAY|GREY|PINK|PURPLE|ORANGE|BROWN|NAVY|BEIGE|SILVER|GOLD|TAN|CREAM|IVORY|MAROON|BURGUNDY|TURQUOISE|TEAL|OLIVE|LIME|MINT|CORAL|SALMON|PEACH|ROSE|LAVENDER|VIOLET|INDIGO|CYAN|MAGENTA|AMBER|COPPER|BRONZE|PLATINUM|CHALK|SAGE|STONE|SAND|PEARL|CHAMPAGNE))',
            ]
            
            for pattern in sku_color_patterns:
                match = re.search(pattern, sku, re.IGNORECASE)
                if match:
                    color_from_sku = match.group(1).strip().replace('_', ' ')
                    if color_from_sku and color_from_sku not in colors:
                        colors.append(color_from_sku)
        
        # Extract from JavaScript data (variants)
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string and ('variants' in script.string or 'productVariants' in script.string):
                script_content = script.string
                
                # Look for color data in variants
                variant_patterns = [
                    r'var\s+variants\s*=\s*(\[.*?\]);',
                    r'var\s+productVariants\s*=\s*(\[.*?\]);',
                    r'variants:\s*(\[.*?\])',
                    r'productVariants:\s*(\[.*?\])'
                ]
                
                for pattern in variant_patterns:
                    matches = re.findall(pattern, script_content, re.DOTALL)
                    for match in matches:
                        try:
                            variants_data = json.loads(match)
                            for variant in variants_data:
                                if isinstance(variant, dict):
                                    # Extract color from title or options
                                    title = variant.get('title', '')
                                    options = variant.get('options', [])
                                    
                                    # Look for color in title (e.g., "LIGHT CHALK / XS")
                                    if '/' in title:
                                        color_part = title.split('/')[0].strip()
                                        if color_part and color_part not in colors:
                                            colors.append(color_part)
                                    
                                    # Look for color in options array
                                    for option in options:
                                        if option and option not in colors and len(option) <= 30:
                                            colors.append(option)
                        except (json.JSONDecodeError, ValueError):
                            continue
        
        # Final color validation and deduplication - prioritize actual colors
        if colors:
            # Separate title colors from other colors for prioritization
            title_colors = []
            other_colors = []
            
            # Check which colors came from title (higher priority)
            if 'name' in product_data:
                title = product_data['name'].lower()
                for color in colors:
                    color_lower = color.lower()
                    # Check if color is in title OR if it's a translated color from title
                    is_title_color = (color_lower in title or 
                                    any(word in title for word in color_lower.split()) or
                                    # Check if this color was translated from a word in the title
                                    any(word in title for word in ['raven', 'midnight', 'charcoal', 'ebony', 'jet', 'onyx', 'obsidian', 'coal', 'ink', 'shadow']))
                    
                    if is_title_color:
                        title_colors.append(color)
                    else:
                        other_colors.append(color)
            else:
                other_colors = colors
            
            # Process title colors first (higher priority)
            unique_colors = []
            seen_colors = set()
            
            # Process title colors first with less strict filtering
            for color in title_colors:
                color = color.strip()
                if color and color not in seen_colors:
                    # Less strict filtering for title colors since they're usually accurate
                    size_patterns = [
                        r'^(XS|S|M|L|XL|XXL|XXXL)$',
                        r'^\d+$',
                        r'^\d+\/\d+$',
                        r'^\d+-\d+$',
                        r'^(size|sizes?|price|cost|kr|€|\$|£|¥|₹|USD|EUR|GBP)$',
                        r'\/\s*(XS|S|M|L|XL|XXL|XXXL)$',
                        r'.*\/(XS|S|M|L|XL|XXL|XXXL)$',
                    ]
                    
                    is_size = False
                    for pattern in size_patterns:
                        if re.search(pattern, color, re.IGNORECASE):
                            is_size = True
                            break
                    
                    if not is_size and len(color) >= 2:  # More lenient for title colors
                        seen_colors.add(color)
                        unique_colors.append(color)
            
            # Process other colors with stricter filtering
            for color in other_colors:
                color = color.strip()
                if color and color not in seen_colors:
                    # Filter out sizes and other non-color terms
                    size_patterns = [
                        r'^(XS|S|M|L|XL|XXL|XXXL)$',
                        r'^\d+$',
                        r'^\d+\/\d+$',
                        r'^\d+-\d+$',
                        r'^(size|sizes?|price|cost|kr|€|\$|£|¥|₹|USD|EUR|GBP)$',
                        r'\/\s*(XS|S|M|L|XL|XXL|XXXL)$',
                        r'.*\/(XS|S|M|L|XL|XXL|XXXL)$',
                    ]
                    
                    # Filter out dummy/generic product descriptions
                    dummy_patterns = [
                        r'flip\s*flops?',
                        r'sandals?',
                        r'shoes?',
                        r'select\s*colour?',
                        r'choose\s*colour?',
                        r'color\s*option',
                        r'available\s*colors?',
                        r'product\s*color',
                        r'generic',
                        r'dummy',
                        r'placeholder',
                        r'click\s*to\s*select',
                        r'select\s*size',
                        r'choose\s*size',
                        r'premium\s*slide',  # Filter out "Premium Slide sand"
                        r'slide\s*sand',     # Filter out generic slide descriptions
                        r'construction',     # Filter out construction details
                        r'material',         # Filter out material descriptions
                        r'style',           # Filter out style numbers
                        r'embossed',         # Filter out embossed details
                        r'ergonomic',        # Filter out ergonomic details
                        r'custom',           # Filter out custom details
                        r'injected',         # Filter out material details
                        r'rubber',           # Filter out material names
                        r'eva',              # Filter out material names
                        r'footbed',          # Filter out footbed details
                        r'strap',            # Filter out strap details
                        r'sole',             # Filter out sole details
                        r'logo',             # Filter out logo details
                        r'monogram',         # Filter out monogram details
                        r'tread',            # Filter out tread details
                        r'contoured',        # Filter out contoured details
                        r'grippy',           # Filter out grippy details
                        r'lightweight',      # Filter out lightweight details
                        r'minimal',          # Filter out minimal details
                        r'versatility',     # Filter out versatility details
                        r'aesthetic',       # Filter out aesthetic details
                        r'sporty',          # Filter out sporty details
                        r'comfort',         # Filter out comfort details
                        r'cool-down',       # Filter out cool-down details
                        r'lounging',        # Filter out lounging details
                        r'post-workout',    # Filter out post-workout details
                        r'home',            # Filter out home details
                    ]
                    
                    is_size = False
                    is_dummy = False
                    
                    # Check for size patterns
                    for pattern in size_patterns:
                        if re.search(pattern, color, re.IGNORECASE):
                            is_size = True
                            break
                    
                    # Check for dummy patterns
                    for pattern in dummy_patterns:
                        if re.search(pattern, color, re.IGNORECASE):
                            is_dummy = True
                            break
                    
                    # Check if it's too generic
                    is_generic = False
                    if len(color.split()) == 1 and color.lower() in ['white', 'black', 'blue', 'red', 'green', 'yellow', 'pink', 'purple', 'orange', 'brown', 'gray', 'grey', 'sand']:
                        is_generic = True
                    
                    # Only add if it's not a size, not dummy, not generic, and contains color-related words
                    if not is_size and not is_dummy and not is_generic and len(color) >= 3:
                        seen_colors.add(color)
                        unique_colors.append(color)
            
            if unique_colors:
                product_data['colors'] = unique_colors

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
            # Filter out color information from specifications
            specifications = [s for s in specifications if not re.search(r'colour|color|kleur', s, re.IGNORECASE)]
            if specifications:
                product_data['specifications'] = specifications

        # Extract additional metadata
        meta_tags = soup.find_all('meta')
        for meta in meta_tags:
            name = meta.get('name', '').lower()
            content = meta.get('content', '')
            if name in ['keywords', 'author'] and content:
                product_data[name] = content
        
        # Use AI model for enhanced extraction if available and enabled
        if AI_MODEL_AVAILABLE and USE_AI_MODEL:
            try:
                product_data = extract_with_model(product_data)
            except Exception as e:
                print(f"AI model extraction failed: {e}")
                # Continue with basic extraction
        
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
    app.run(debug=True, host='0.0.0.0', port=5010)
