#!/usr/bin/env python3
"""
Debug script to analyze ODD MOLLY page structure
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, urlparse

def debug_oddmolly_page():
    """Debug the ODD MOLLY page to see what size elements exist"""
    url = "https://oddmolly.com/products/garden-blouse-1"
    
    print("DEBUGGING ODD MOLLY PAGE")
    print("=" * 50)
    print(f"URL: {url}")
    print("-" * 50)
    
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
                if any(currency in price_text for currency in ['€', '$', '₹', '£', '¥', 'kr']):
                    print(f"Price: {price_text}")
                    break
        
        print("\n🔍 ANALYZING PAGE STRUCTURE:")
        print("-" * 40)
        
        # Look for any elements that might contain sizes
        print("1. Looking for buttons with size-related text...")
        all_buttons = soup.find_all('button')
        size_buttons = []
        for button in all_buttons:
            text = button.get_text().strip()
            if text and len(text) <= 10:
                # Check if it looks like a size
                if re.search(r'\b(XS|S|M|L|XL|XXL|\d+)\b', text, re.IGNORECASE):
                    size_buttons.append(text)
        
        if size_buttons:
            print(f"   Found potential size buttons: {size_buttons}")
        else:
            print("   No size buttons found")
        
        print("\n2. Looking for select elements...")
        selects = soup.find_all('select')
        for select in selects:
            name = select.get('name', '')
            id_attr = select.get('id', '')
            class_attr = ' '.join(select.get('class', []))
            print(f"   Select: name='{name}', id='{id_attr}', class='{class_attr}'")
            
            options = select.find_all('option')
            for option in options:
                text = option.get_text().strip()
                if text and len(text) <= 10:
                    print(f"     Option: '{text}'")
        
        print("\n3. Looking for divs/spans with size-related classes...")
        size_elements = soup.find_all(['div', 'span'], class_=re.compile(r'size|variant|option', re.I))
        for element in size_elements:
            text = element.get_text().strip()
            if text and len(text) <= 10:
                classes = ' '.join(element.get('class', []))
                print(f"   Element: '{text}' (classes: {classes})")
        
        print("\n4. Looking for any text containing size patterns...")
        page_text = soup.get_text()
        size_patterns = [
            r'\b(XS|S|M|L|XL|XXL)\b',
            r'\b(\d+\/\d+)\b',
            r'\b(\d+-\d+)\b',
            r'Size[:\s]*([A-Z0-9\s,\.\-\/]+)',
            r'Sizes?[:\s]*([A-Z0-9\s,\.\-\/]+)'
        ]
        
        for pattern in size_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                print(f"   Pattern '{pattern}': {matches}")
        
        print("\n5. Looking for specific ODD MOLLY selectors...")
        # Try some specific selectors that might work for ODD MOLLY
        oddmolly_selectors = [
            '.product-variants',
            '.variant-selector',
            '.size-selector',
            '.product-options',
            '.size-options',
            '.variant-options',
            '[data-variant]',
            '[data-size]',
            '.product-form__variants',
            '.product-form__variant',
            '.variant-picker',
            '.size-picker'
        ]
        
        for selector in oddmolly_selectors:
            elements = soup.select(selector)
            if elements:
                print(f"   Selector '{selector}': Found {len(elements)} elements")
                for element in elements:
                    text = element.get_text().strip()
                    if text:
                        print(f"     Text: '{text[:100]}...'")
        
        print("\n6. Looking for JavaScript/JSON data...")
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string:
                script_content = script.string
                if 'size' in script_content.lower() or 'variant' in script_content.lower():
                    # Look for JSON-like data
                    json_matches = re.findall(r'\{[^{}]*"[^"]*size[^"]*"[^{}]*\}', script_content, re.IGNORECASE)
                    if json_matches:
                        print(f"   Found JSON with size data: {json_matches}")
        
        print("\n7. Full page text analysis (first 2000 chars)...")
        print("-" * 40)
        print(page_text[:2000])
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_oddmolly_page()
