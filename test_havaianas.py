#!/usr/bin/env python3
"""
Test script specifically for Havaianas size extraction
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, urlparse
import time

def test_havaianas_extraction():
    """Test size extraction specifically for Havaianas"""
    url = "https://havaianas-store.com/it/en/havaianas-top-logomania-colors-ii/4147526-INDIGO_BLUE.html"
    
    print(f"Testing HAVAIANAS SIZE EXTRACTION")
    print(f"URL: {url}")
    print("=" * 60)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print("✅ Page loaded successfully")
        
        # Extract basic product info
        product_name = soup.find('h1')
        if product_name:
            print(f"Product Name: {product_name.get_text().strip()}")
        
        # Look for price
        price_selectors = ['.price', '.product-price', '[data-testid="price"]', '.current-price']
        for selector in price_selectors:
            price_element = soup.select_one(selector)
            if price_element:
                price_text = price_element.get_text().strip()
                if any(currency in price_text for currency in ['€', '$', '₹', '£', '¥']):
                    print(f"Price: {price_text}")
                    break
        
        # Focus on size extraction
        print("\n🔍 SIZE EXTRACTION ANALYSIS:")
        print("-" * 40)
        
        sizes = []
        
        # Enhanced size selectors for Havaianas
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
        
        print(f"Testing {len(size_selectors)} size selectors...")
        
        for i, selector in enumerate(size_selectors):
            size_elements = soup.select(selector)
            if size_elements:
                print(f"✅ Selector {i+1}: '{selector}' found {len(size_elements)} elements")
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
                        'Fit', 'Fitting', 'Fit Guide', 'Size Help'
                    ]
                    
                    if size_text and size_text not in skip_texts:
                        # Clean the size text
                        size_text = re.sub(r'[^\w\s\-\.\/]', '', size_text).strip()
                        
                        # Check if it looks like a size (contains common size patterns)
                        size_patterns = [
                            r'\b(XS|S|M|L|XL|XXL|XXXL)\b',  # Letter sizes
                            r'\b(\d+(?:\.\d+)?)\b',  # Numeric sizes
                            r'\b(\d+[A-Z]?)\b',  # Numeric with optional letter
                            r'\b([A-Z]\d+)\b',  # Letter followed by number
                            r'\b(\d+[A-Z]+\d*)\b',  # Complex patterns
                            r'\b(\d+\/\d+)\b',  # Range sizes like 33/34, 35/36
                            r'\b(\d+-\d+)\b',  # Range sizes like 33-34, 35-36
                            r'\b(\d+\.\d+\/\d+\.\d+)\b',  # Decimal ranges like 7.5/8.5
                            r'\b(\d+\.\d+-\d+\.\d+)\b'  # Decimal ranges like 7.5-8.5
                        ]
                        
                        is_valid_size = False
                        for pattern in size_patterns:
                            if re.search(pattern, size_text, re.IGNORECASE):
                                is_valid_size = True
                                break
                        
                        if is_valid_size and len(size_text) <= 15:  # Reasonable size length
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
                            print(f"  📏 Found size: '{size_text}' ({availability})")
            else:
                print(f"❌ Selector {i+1}: '{selector}' found 0 elements")
        
        # Remove duplicates
        unique_sizes = []
        seen_sizes = set()
        for size_info in sizes:
            size = size_info['size']
            if size not in seen_sizes:
                seen_sizes.add(size)
                unique_sizes.append(size_info)
        
        print(f"\n📊 FINAL RESULTS:")
        print("-" * 40)
        if unique_sizes:
            print(f"✅ Found {len(unique_sizes)} unique sizes:")
            for size_info in unique_sizes:
                print(f"  - {size_info['size']} ({size_info['availability']})")
        else:
            print("❌ No sizes found!")
        
        # Also check page text for size information
        print(f"\n🔍 TEXT ANALYSIS:")
        print("-" * 40)
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
                print(f"📝 Found in text: '{size_text}'")
                break
        
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_havaianas_extraction()
