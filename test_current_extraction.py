#!/usr/bin/env python3
"""
Quick test of current color extraction capabilities
"""

import requests
from bs4 import BeautifulSoup
import re
import json

def extract_colors_from_url(url):
    """Extract colors from a product URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract product name
        product_name = ""
        h1_tags = soup.find_all('h1')
        for h1 in h1_tags:
            if h1.get_text().strip():
                product_name = h1.get_text().strip()
                break
        
        if not product_name:
            product_name = soup.find('title').get_text().strip() if soup.find('title') else "Unknown Product"
        
        # Extract colors using multiple methods
        colors = []
        
        # Method 1: Look for color in title
        if product_name:
            title_color_patterns = [
                r'-\s*([a-z\s]+(?:blue|red|green|yellow|black|white|gray|grey|pink|purple|orange|brown|navy|beige|silver|gold|tan|cream|ivory|maroon|burgundy|turquoise|teal|olive|lime|mint|coral|salmon|peach|rose|lavender|violet|indigo|cyan|magenta|amber|copper|bronze|platinum|chalk|sage|stone|sand|pearl|champagne|raven|midnight|charcoal|ebony|jet|onyx|obsidian|coal|ink|shadow|dark|light|bright|deep|soft|vivid|pale|rich|warm|cool|neutral|pastel|metallic|matte|glossy|satin))',
                r'([a-z\s]+(?:blue|red|green|yellow|black|white|gray|grey|pink|purple|orange|brown|navy|beige|silver|gold|tan|cream|ivory|maroon|burgundy|turquoise|teal|olive|lime|mint|coral|salmon|peach|rose|lavender|violet|indigo|cyan|magenta|amber|copper|bronze|platinum|chalk|sage|stone|sand|pearl|champagne|raven|midnight|charcoal|ebony|jet|onyx|obsidian|coal|ink|shadow|dark|light|bright|deep|soft|vivid|pale|rich|warm|cool|neutral|pastel|metallic|matte|glossy|satin))',
                r'\b(raven|midnight|charcoal|ebony|jet|onyx|obsidian|coal|ink|shadow|crimson|scarlet|burgundy|maroon|navy|royal|sky|ocean|forest|emerald|lime|mint|sage|olive|khaki|camel|tan|beige|cream|ivory|pearl|champagne|rose|blush|coral|salmon|peach|apricot|amber|honey|gold|bronze|copper|silver|platinum|gunmetal|steel)\b',
            ]
            
            for pattern in title_color_patterns:
                match = re.search(pattern, product_name, re.IGNORECASE)
                if match:
                    if match.groups():
                        color_from_title = match.group(1).strip()
                    else:
                        color_from_title = match.group(0).strip()
                    
                    # Translate specific color names
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
                    
                    color_lower = color_from_title.lower().strip()
                    if color_lower in color_translations:
                        translated_color = color_translations[color_lower]
                        colors.append(translated_color)
                    else:
                        colors.append(color_from_title)
                    break
        
        # Method 2: Look for color selectors
        color_selectors = [
            '.color', '.colour', '.color-option', '.color-choice', '.color-variant',
            '.swatch', '.color-swatch', '.product-color', '.variant-color',
            '.color-dropdown', '.color-selector', '.color-picker', '.swatch-btn',
            '[data-color]', '[data-colour]', '.color-name', '.colour-name'
        ]
        
        for selector in color_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text().strip()
                if text and len(text) < 50 and text not in colors:
                    colors.append(text)
        
        # Method 3: Look for meta tags
        meta_tags = soup.find_all('meta', {'name': re.compile(r'color|colour', re.I)})
        for meta in meta_tags:
            content = meta.get('content', '').strip()
            if content and content not in colors:
                colors.append(content)
        
        # Filter and deduplicate colors
        unique_colors = []
        seen_colors = set()
        
        for color in colors:
            color = color.strip()
            if color and color not in seen_colors and len(color) >= 2:
                # Filter out generic terms
                if color.lower() not in ['select', 'choose', 'option', 'variant', 'color', 'colour']:
                    seen_colors.add(color)
                    unique_colors.append(color)
        
        return {
            'product_name': product_name,
            'colors': unique_colors,
            'url': url
        }
        
    except Exception as e:
        return {
            'product_name': 'Error',
            'colors': [],
            'url': url,
            'error': str(e)
        }

def test_multiple_urls():
    """Test color extraction on multiple URLs"""
    test_urls = [
        "https://eu.sergiotacchini.com/products/cup-slide-raven",
        "https://oddmolly.com/products/garden-blouse-1",
        "https://www.nike.com/t/air-max-270-mens-shoes-KkLcGr",
        "https://www.zara.com/us/en/woman/t-shirts-c358002.html"
    ]
    
    print("=" * 70)
    print("TESTING CURRENT COLOR EXTRACTION CAPABILITIES")
    print("=" * 70)
    
    for i, url in enumerate(test_urls, 1):
        print(f"\nTest {i}: {url}")
        print("-" * 50)
        
        result = extract_colors_from_url(url)
        
        print(f"Product: {result['product_name']}")
        print(f"Colors: {result['colors']}")
        
        if 'error' in result:
            print(f"Error: {result['error']}")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    test_multiple_urls()
