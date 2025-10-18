#!/usr/bin/env python3
"""
Test script to debug colors section visibility
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urlparse

def test_color_extraction(url):
    """Test color extraction for a specific URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"Testing URL: {url}")
        print("-" * 60)
        
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
        
        print("📊 Structured Data Found:")
        for key, value in product_data.items():
            print(f"  {key}: {value}")
        
        # Extract title/name
        if 'name' not in product_data:
            title_selectors = ['h1', '.product-title', '.product-name', '[data-testid="product-title"]']
            for selector in title_selectors:
                title_element = soup.select_one(selector)
                if title_element:
                    product_data['name'] = title_element.get_text().strip()
                    break
        
        print(f"\n📝 Product Name: {product_data.get('name', 'N/A')}")
        
        # Enhanced color extraction
        colors = []
        
        # Extract from structured data first
        if 'color' in product_data:
            color_value = product_data['color']
            if isinstance(color_value, list):
                colors.extend(color_value)
            else:
                colors.append(str(color_value))
            print(f"🎨 Colors from structured data: {colors}")
        
        # Extract from meta tags
        color_meta = soup.find('meta', {'property': 'product:color'}) or soup.find('meta', {'name': 'color'})
        if color_meta:
            color_content = color_meta.get('content', '').strip()
            if color_content and color_content not in colors:
                colors.append(color_content)
                print(f"🎨 Colors from meta tags: {color_content}")
        
        # Extract from color selectors
        color_selectors = [
            '.color', '.product-color', '.color-option', '.color-variant',
            '[data-color]', '.color-name', '.color-value', '.swatch-color',
            '.color-swatch', '.color-picker', '.color-selector', '.available-colors',
            '[itemprop="color"]', '.product-colors', '.color-list'
        ]
        
        print(f"\n🔍 Searching for color selectors...")
        for selector in color_selectors:
            color_elements = soup.select(selector)
            if color_elements:
                print(f"  Found {len(color_elements)} elements with selector: {selector}")
                for element in color_elements:
                    color_text = element.get_text().strip()
                    if color_text and len(color_text) <= 50:
                        print(f"    Color text: '{color_text}'")
                        color_text = re.sub(r'[^\w\s\-\.\/]', '', color_text).strip()
                        if color_text and color_text not in colors:
                            colors.append(color_text)
        
        # Extract from page text patterns
        page_text = soup.get_text()
        print(f"\n🔍 Searching page text for color patterns...")
        
        color_patterns = [
            r'(?:Available Colors?|Color Options?|Colors? Available)\s*:?\s*([A-Za-z\s,\.\-\/]+)',
            r'(?:Color|Colors?)\s*:?\s*([A-Za-z\s,\.\-\/]+)',
            r'(?:Available in|Comes in)\s*:?\s*([A-Za-z\s,\.\-\/]+)',
            r'(?:Color Selection|Color Range)\s*:?\s*([A-Za-z\s,\.\-\/]+)',
            r'(?:Colour|Kleur)\s*:?\s*([A-Za-z\s,\.\-\/]+)',  # Dutch/UK spelling
            r'(\w+\s+(?:blue|red|green|yellow|black|white|gray|grey|pink|purple|orange|brown|navy|beige|silver|gold|tan|cream|ivory|maroon|burgundy|turquoise|teal|olive|lime|mint|coral|salmon|peach|rose|lavender|violet|indigo|cyan|magenta|amber|copper|bronze|platinum))',  # Color + descriptor patterns
            r'([A-Z][A-Z\s]+(?:CHALK|MINT|SAGE|STONE|SAND|PEARL|CREAM|IVORY|CHAMPAGNE|COPPER|BRONZE|ROSE|CORAL|SALMON|PEACH|LAVENDER|VIOLET|INDIGO|CYAN|MAGENTA|AMBER))',  # Specific color names
        ]
        
        for pattern in color_patterns:
            text_match = re.search(pattern, page_text, re.IGNORECASE)
            if text_match:
                color_text = text_match.group(1).strip()
                print(f"  Found color pattern '{pattern}': '{color_text}'")
                color_list = re.split(r'[,;|\n\r]', color_text)
                for color_item in color_list:
                    color_item = color_item.strip()
                    if color_item and len(color_item) <= 30 and color_item not in colors:
                        if (re.search(r'\b(blue|red|green|yellow|black|white|gray|grey|pink|purple|orange|brown|navy|beige|silver|gold|tan|cream|ivory|maroon|burgundy|turquoise|teal|olive|lime|mint|coral|salmon|peach|rose|lavender|violet|indigo|cyan|magenta|amber|copper|bronze|platinum|chalk|sage|stone|sand|pearl|champagne)\b', color_item, re.IGNORECASE) or
                            re.search(r'\b[A-Z][A-Z\s]*(?:CHALK|MINT|SAGE|STONE|SAND|PEARL|CREAM|IVORY|CHAMPAGNE|COPPER|BRONZE|ROSE|CORAL|SALMON|PEACH|LAVENDER|VIOLET|INDIGO|CYAN|MAGENTA|AMBER)\b', color_item)):
                            colors.append(color_item)
                            print(f"    Added color: '{color_item}'")
        
        # Extract from product title
        if 'name' in product_data:
            title = product_data['name']
            print(f"\n🔍 Searching product title for colors: '{title}'")
            
            # Look for color patterns in title like "Antony - soft blue"
            title_color_patterns = [
                r'-\s*([a-z\s]+(?:blue|red|green|yellow|black|white|gray|grey|pink|purple|orange|brown|navy|beige|silver|gold|tan|cream|ivory|maroon|burgundy|turquoise|teal|olive|lime|mint|coral|salmon|peach|rose|lavender|violet|indigo|cyan|magenta|amber|copper|bronze|platinum))',
                r'([a-z\s]+(?:blue|red|green|yellow|black|white|gray|grey|pink|purple|orange|brown|navy|beige|silver|gold|tan|cream|ivory|maroon|burgundy|turquoise|teal|olive|lime|mint|coral|salmon|peach|rose|lavender|violet|indigo|cyan|magenta|amber|copper|bronze|platinum))',
            ]
            
            for pattern in title_color_patterns:
                match = re.search(pattern, title, re.IGNORECASE)
                if match:
                    color_from_title = match.group(1).strip()
                    if color_from_title and color_from_title not in colors:
                        colors.append(color_from_title)
                        print(f"  Found color in title: '{color_from_title}'")
        
        print(f"\n🎨 All colors found: {colors}")
        
        # Final color validation and deduplication
        if colors:
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
                        r'^(size|sizes?|price|cost|kr|€|\$|£|¥|₹|USD|EUR|GBP)$',
                        r'\/\s*(XS|S|M|L|XL|XXL|XXXL)$',  # Filter out "LIGHT CHALK / XS" type
                        r'.*\/(XS|S|M|L|XL|XXL|XXXL)$',  # Filter out anything ending with /XS, /S, etc.
                    ]
                    
                    is_size = False
                    for pattern in size_patterns:
                        if re.search(pattern, color, re.IGNORECASE):
                            is_size = True
                            break
                    
                    # Only add if it's not a size and contains color-related words
                    if not is_size and len(color) >= 3:
                        seen_colors.add(color)
                        unique_colors.append(color)
            
            print(f"✅ Final unique colors: {unique_colors}")
            if unique_colors:
                product_data['colors'] = unique_colors
            else:
                print("❌ No valid colors found after filtering")
        else:
            print("❌ No colors found at all")
        
        return product_data
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {'error': str(e)}

if __name__ == "__main__":
    # Test with a URL that should have colors
    test_urls = [
        "https://oddmolly.com/products/garden-blouse-1",
        # Add the retourjeans URL if you have it
    ]
    
    for url in test_urls:
        result = test_color_extraction(url)
        print("\n" + "="*80)
        print(f"FINAL RESULT FOR {url}")
        print("="*80)
        if 'colors' in result:
            print(f"✅ Colors: {result['colors']}")
        else:
            print("❌ No colors found")
        print("="*80)
