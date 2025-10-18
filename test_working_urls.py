#!/usr/bin/env python3
"""
Test with a simple working URL that definitely has sizes
"""

import requests
from bs4 import BeautifulSoup
import json
import re

def test_simple_working_url():
    """Test with a simple working URL"""
    # Using a simple test page or a known working e-commerce site
    test_urls = [
        "https://oddmolly.com/products/garden-blouse-1",  # Original
        "https://www.amazon.com/dp/B08N5WRWNW",  # Amazon product (usually has sizes)
        "https://www.target.com/p/men-s-basic-t-shirt-goodfellow-co/-/A-75564000"  # Target product
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for i, url in enumerate(test_urls):
        print(f"\nTest {i+1}: {url}")
        print("-" * 50)
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            print("✅ Page loaded successfully")
            
            # Extract basic info
            title = soup.find('h1') or soup.find('title')
            if title:
                print(f"Title: {title.get_text().strip()[:100]}...")
            
            # Look for sizes using a very broad approach
            print("\n🔍 Looking for sizes...")
            
            # Method 1: Look for any text that looks like sizes
            page_text = soup.get_text()
            size_patterns = [
                r'\b(XS|S|M|L|XL|XXL|XXXL)\b',
                r'\b(\d+\/\d+)\b',
                r'\b(\d+-\d+)\b',
                r'\b(\d+\.\d+)\b',
                r'\b(\d+)\b'
            ]
            
            found_sizes = set()
            for pattern in size_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    if match and len(match) <= 10:
                        # Skip obvious non-sizes
                        if not re.search(r'\d+\s*(kr|€|\$|£|¥|₹|USD|EUR|GBP)', match, re.IGNORECASE):
                            found_sizes.add(match)
            
            if found_sizes:
                print(f"✅ Found potential sizes: {sorted(found_sizes)}")
            else:
                print("❌ No sizes found in text")
            
            # Method 2: Look for specific HTML elements
            print("\n🔍 Looking for size elements...")
            size_elements = []
            
            # Look for buttons
            buttons = soup.find_all('button')
            for button in buttons:
                text = button.get_text().strip()
                if text and len(text) <= 10:
                    if re.search(r'\b(XS|S|M|L|XL|XXL|\d+)\b', text, re.IGNORECASE):
                        size_elements.append(f"Button: '{text}'")
            
            # Look for options
            options = soup.find_all('option')
            for option in options:
                text = option.get_text().strip()
                if text and len(text) <= 10:
                    if re.search(r'\b(XS|S|M|L|XL|XXL|\d+)\b', text, re.IGNORECASE):
                        size_elements.append(f"Option: '{text}'")
            
            # Look for spans/divs with size-related classes
            elements = soup.find_all(['span', 'div'], class_=re.compile(r'size|variant|option', re.I))
            for element in elements:
                text = element.get_text().strip()
                if text and len(text) <= 10:
                    if re.search(r'\b(XS|S|M|L|XL|XXL|\d+)\b', text, re.IGNORECASE):
                        classes = ' '.join(element.get('class', []))
                        size_elements.append(f"Element: '{text}' (class: {classes})")
            
            if size_elements:
                print(f"✅ Found size elements:")
                for element in size_elements[:10]:  # Show first 10
                    print(f"  - {element}")
            else:
                print("❌ No size elements found")
            
            # Method 3: Look for structured data
            print("\n🔍 Looking for structured data...")
            script_tags = soup.find_all('script', type='application/ld+json')
            for script in script_tags:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'Product':
                        offers = data.get('offers', [])
                        if isinstance(offers, list):
                            for offer in offers:
                                if isinstance(offer, dict) and 'sku' in offer:
                                    sku = offer['sku']
                                    if '/' in sku or '-' in sku:
                                        print(f"  Found SKU with size info: {sku}")
                except:
                    continue
            
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_simple_working_url()
