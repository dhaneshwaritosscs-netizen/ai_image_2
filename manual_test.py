#!/usr/bin/env python3
"""
Simple manual test to see what's actually on the ODD MOLLY page
"""

import requests
from bs4 import BeautifulSoup
import re

def manual_oddmolly_test():
    """Manually inspect the ODD MOLLY page"""
    url = "https://oddmolly.com/products/garden-blouse-1"
    
    print("MANUAL ODD MOLLY INSPECTION")
    print("=" * 50)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print("✅ Page loaded successfully")
        print(f"Page title: {soup.title.string if soup.title else 'No title'}")
        
        # Look for the product name
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags:
            print(f"H1: {h1.get_text().strip()}")
        
        # Look for price
        price_elements = soup.find_all(text=re.compile(r'\d+\s*kr'))
        for price in price_elements:
            print(f"Price found: {price.strip()}")
        
        # Look for any text that might be sizes
        print("\n🔍 Searching for size-related text...")
        
        # Get all text content
        all_text = soup.get_text()
        
        # Look for common size patterns
        size_patterns = [
            r'\b(XS|S|M|L|XL|XXL)\b',
            r'\b(\d+\/\d+)\b',
            r'\b(\d+-\d+)\b',
            r'Size[:\s]*([A-Z0-9\s,]+)',
            r'Sizes?[:\s]*([A-Z0-9\s,]+)'
        ]
        
        for pattern in size_patterns:
            matches = re.findall(pattern, all_text, re.IGNORECASE)
            if matches:
                print(f"Pattern '{pattern}': {matches}")
        
        # Look for any buttons or clickable elements
        print("\n🔍 Looking for buttons and clickable elements...")
        buttons = soup.find_all(['button', 'a', 'div'], class_=True)
        for button in buttons:
            text = button.get_text().strip()
            classes = ' '.join(button.get('class', []))
            if text and len(text) <= 20:
                print(f"Element: '{text}' (classes: {classes})")
        
        # Look for select elements
        print("\n🔍 Looking for select elements...")
        selects = soup.find_all('select')
        for select in selects:
            name = select.get('name', '')
            id_attr = select.get('id', '')
            print(f"Select: name='{name}', id='{id_attr}'")
            options = select.find_all('option')
            for option in options:
                text = option.get_text().strip()
                if text:
                    print(f"  Option: '{text}'")
        
        # Look for any elements with size-related attributes
        print("\n🔍 Looking for elements with size-related attributes...")
        size_elements = soup.find_all(attrs={'data-size': True})
        for element in size_elements:
            print(f"Element with data-size: {element.get_text().strip()}")
        
        variant_elements = soup.find_all(attrs={'data-variant': True})
        for element in variant_elements:
            print(f"Element with data-variant: {element.get_text().strip()}")
        
        # Check if there are any JavaScript variables with size data
        print("\n🔍 Looking for JavaScript size data...")
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and ('size' in script.string.lower() or 'variant' in script.string.lower()):
                script_text = script.string
                # Look for common patterns
                if 'S' in script_text and 'M' in script_text and 'L' in script_text:
                    print("Found potential size data in script")
                    # Extract relevant part
                    lines = script_text.split('\n')
                    for line in lines:
                        if 'size' in line.lower() or 'variant' in line.lower():
                            print(f"  {line.strip()}")
        
        # Print a sample of the HTML to see the structure
        print("\n🔍 Sample HTML structure...")
        body = soup.find('body')
        if body:
            # Get first 2000 characters of HTML
            html_sample = str(body)[:2000]
            print(html_sample)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    manual_oddmolly_test()
