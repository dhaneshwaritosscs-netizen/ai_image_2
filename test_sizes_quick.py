#!/usr/bin/env python3
"""
Quick test for size extraction without AI model
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, urlparse
import time

def extract_sizes_only(url):
    """Extract only size information from a URL"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        sizes = []
        
        # Enhanced size selectors
        size_selectors = [
            '.size-selector button', '.size-option', '.size-button',
            'select[name*="size"] option', '.product-size', '.size-variant',
            '[data-testid*="size"]', '.variant-size', '.size-selector',
            '.size-options button', '.size-list button', '.size-grid button',
            '.size-picker button', '.size-chooser button', '.size-item',
            'button[data-size]', '.size-btn', '.size-option-btn',
            '.size-select', '.size-dropdown', '.size-chooser',
            '.product-variant', '.variant-selector', '.size-list',
            '.size-grid', '.size-options', '.size-picker',
            '.size-selector-item', '.size-item-button', '.size-choice',
            '.size-selector-option', '.size-selector-item',
            '[data-size]', '[data-variant]', '[data-option]',
            '[data-value*="size"]', '[data-name*="size"]',
            '.size', '.sizes', '.size-option', '.size-choice',
            '.variant', '.variants', '.option', '.options',
            '.swatch-option', '.swatch', '.swatch-element',
            '.product-options', '.product-option', '.option-value',
            '.attribute-option', '.attribute-options',
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
                    
                    # Check if it looks like a size
                    size_patterns = [
                        r'\b(XS|S|M|L|XL|XXL|XXXL)\b',  # Letter sizes
                        r'\b(\d+\/\d+)\b',  # Range sizes like 33/34, 35/36
                        r'\b(\d+-\d+)\b',  # Range sizes like 33-34, 35-36
                        r'\b(\d+\.\d+\/\d+\.\d+)\b',  # Decimal ranges like 7.5/8.5
                        r'\b(\d+\.\d+-\d+\.\d+)\b',  # Decimal ranges like 7.5-8.5
                        r'\b(\d+[A-Z]?)\b',  # Numeric with optional letter
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
                    
                    if is_valid_size and len(size_text) <= 10:
                        # Check availability
                        availability = 'In Stock'
                        class_names = ' '.join(element.get('class', []))
                        if any(word in class_names.lower() for word in ['disabled', 'unavailable', 'out-of-stock', 'sold-out']):
                            availability = 'Out of Stock'
                        
                        if element.get('disabled') or element.get('aria-disabled') == 'true':
                            availability = 'Out of Stock'
                        
                        if element.get('data-available') == 'false':
                            availability = 'Out of Stock'
                        
                        sizes.append({
                            'size': size_text,
                            'availability': availability,
                            'selector': selector
                        })
        
        # Extract from JavaScript data (Shopify variants)
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
        
        # Extract from select options (like ODD MOLLY)
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
        
        # Remove duplicates
        unique_sizes = []
        seen_sizes = set()
        for size_info in sizes:
            size = size_info['size']
            if size not in seen_sizes:
                seen_sizes.add(size)
                unique_sizes.append(size_info)
        
        return unique_sizes
        
    except Exception as e:
        return [{'error': str(e)}]

def test_size_extraction_quick():
    """Quick test for size extraction"""
    test_urls = [
        "https://oddmolly.com/products/garden-blouse-1",
        "https://www.nike.com/t/air-max-270-mens-shoes-KkLcGr",
        "https://www.zara.com/us/en/woman/t-shirts-c358002.html"
    ]
    
    print("QUICK SIZE EXTRACTION TEST")
    print("=" * 50)
    
    for i, url in enumerate(test_urls):
        print(f"\nTest {i+1}: {url}")
        print("-" * 40)
        
        sizes = extract_sizes_only(url)
        
        if sizes and 'error' not in sizes[0]:
            print(f"✅ Found {len(sizes)} sizes:")
            for size_info in sizes:
                print(f"  - {size_info['size']} ({size_info['availability']})")
        else:
            print("❌ No sizes found or error occurred")
            if sizes and 'error' in sizes[0]:
                print(f"   Error: {sizes[0]['error']}")

if __name__ == "__main__":
    test_size_extraction_quick()
