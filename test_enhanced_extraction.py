#!/usr/bin/env python3
"""
Test script for enhanced brand, model, and color extraction
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urlparse

def extract_product_data(url):
    """Enhanced product data extraction with brand, model, and color focus"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        product_data = {}
        
        # Extract structured data (JSON-LD)
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'Product':
                    product_data.update(data)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'Product':
                            product_data.update(item)
                            break
            except (json.JSONDecodeError, ValueError):
                continue
        
        # Extract title/name
        if 'name' not in product_data:
            title_selectors = ['h1', '.product-title', '.product-name', '[data-testid="product-title"]']
            for selector in title_selectors:
                title_element = soup.select_one(selector)
                if title_element:
                    product_data['name'] = title_element.get_text().strip()
                    break
        
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
        
        # Final color validation and deduplication
        if colors:
            # Remove duplicates and filter out non-colors
            unique_colors = []
            seen_colors = set()
            
            for color in colors:
                color = color.strip()
                if color and color not in seen_colors:
                    # Filter out sizes and other non-color terms
                    size_patterns = [
                        r'^(XS|S|M|L|XL|XXL|XXXL)$',
                        r'^\d+$',
                        r'^\d+\/\d+$',
                        r'^\d+-\d+$',
                        r'^(size|sizes?|price|cost|kr|€|\$|£|¥|₹|USD|EUR|GBP)$'
                    ]
                    
                    is_size = False
                    for pattern in size_patterns:
                        if re.match(pattern, color, re.IGNORECASE):
                            is_size = True
                            break
                    
                    # Only add if it's not a size and contains color-related words
                    if not is_size and len(color) >= 3:
                        seen_colors.add(color)
                        unique_colors.append(color)
            
            if unique_colors:
                product_data['colors'] = unique_colors
        
        # Extract price
        if 'price' not in product_data:
            price_selectors = ['.price', '.product-price', '[data-testid="price"]', '.cost']
            for selector in price_selectors:
                price_element = soup.select_one(selector)
                if price_element:
                    product_data['price'] = price_element.get_text().strip()
                    break
        
        return product_data
        
    except Exception as e:
        return {'error': str(e)}

def test_urls():
    """Test multiple URLs for brand, model, and color extraction"""
    test_urls = [
        "https://oddmolly.com/products/garden-blouse-1",
        "https://www.nike.com/t/air-max-270-mens-shoes-KkLcGr",
        "https://www.zara.com/us/en/woman/t-shirts-c358002.html"
    ]
    
    print("=" * 80)
    print("ENHANCED BRAND, MODEL & COLOR EXTRACTION TEST")
    print("=" * 80)
    
    for i, url in enumerate(test_urls, 1):
        print(f"\nTest {i}: {url}")
        print("-" * 60)
        
        result = extract_product_data(url)
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            continue
        
        print(f"✅ Product Name: {result.get('name', 'N/A')}")
        print(f"✅ Brand: {result.get('brand', 'N/A')}")
        print(f"✅ Price: {result.get('price', 'N/A')}")
        
        if result.get('colors'):
            print(f"✅ Colors: {', '.join(result['colors'])}")
        else:
            print("❌ No colors found")
        
        print(f"📊 Total fields extracted: {len(result)}")

if __name__ == "__main__":
    test_urls()
