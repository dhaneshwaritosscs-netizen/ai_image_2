#!/usr/bin/env python3
"""
Test the fixed size extraction for ODD MOLLY
"""

import requests
from bs4 import BeautifulSoup
import json
import re

def test_oddmolly_fixed():
    """Test the fixed size extraction for ODD MOLLY"""
    url = "https://oddmolly.com/products/garden-blouse-1"
    
    print("TESTING FIXED ODD MOLLY SIZE EXTRACTION")
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
        
        sizes = []
        
        # Method 1: Extract from JavaScript data (Shopify variants)
        print("\n🔍 Method 1: Extracting from JavaScript data...")
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
                            print(f"   Found {len(variants_data)} variants in JavaScript")
                            
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
                                                print(f"   ✅ Found size: {size_part} ({'In Stock' if available else 'Out of Stock'})")
                                    
                                    # Look for size in options array
                                    for option in options:
                                        if option in ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']:
                                            if option not in [s.get('size', '') for s in sizes]:
                                                sizes.append({
                                                    'size': option,
                                                    'availability': 'In Stock' if available else 'Out of Stock'
                                                })
                                                print(f"   ✅ Found size: {option} ({'In Stock' if available else 'Out of Stock'})")
                        except (json.JSONDecodeError, ValueError) as e:
                            print(f"   ❌ JSON parse error: {e}")
                            continue
        
        # Method 2: Extract from select options
        print("\n🔍 Method 2: Extracting from select options...")
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
                            print(f"   ✅ Found size: {size_part} (In Stock)")
        
        # Remove duplicates
        unique_sizes = []
        seen_sizes = set()
        for size_info in sizes:
            size = size_info['size']
            if size not in seen_sizes:
                seen_sizes.add(size)
                unique_sizes.append(size_info)
        
        print(f"\n📊 FINAL RESULTS:")
        print("-" * 30)
        if unique_sizes:
            print(f"✅ Found {len(unique_sizes)} unique sizes:")
            for size_info in unique_sizes:
                print(f"  - {size_info['size']} ({size_info['availability']})")
        else:
            print("❌ No sizes found!")
        
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_oddmolly_fixed()
