#!/usr/bin/env python3
"""
Test script for product data extraction
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urlparse

def test_extraction(url):
    """Test the extraction on a sample URL"""
    print(f"Testing extraction for: {url}")
    print("-" * 50)
    
    try:
        # Import the extraction function
        from app import extract_product_data
        
        # Extract data
        result = extract_product_data(url)
        
        if 'error' in result:
            print(f"ERROR: {result['error']}")
            return
        
        # Display results
        print("EXTRACTION RESULTS:")
        print("-" * 30)
        print(f"Product Name: {result.get('name', 'N/A')}")
        print(f"Brand: {result.get('brand', 'N/A')}")
        print(f"Price: {result.get('price', 'N/A')}")
        print(f"SKU: {result.get('sku', 'N/A')}")
        print(f"Description: {result.get('description', 'N/A')[:100]}...")
        
        # Display sizes
        if result.get('size_chart'):
            print(f"Sizes: {[s.get('size', '') for s in result['size_chart']]}")
        
        # Display AI extracted data
        if result.get('ai_extracted'):
            print("\nAI EXTRACTED DATA:")
            print("-" * 30)
            ai_data = result['ai_extracted']
            print(f"AI Brand: {ai_data.get('Brand_Name', 'N/A')}")
            print(f"AI Model: {ai_data.get('Models', 'N/A')}")
            print(f"AI Colors: {ai_data.get('Colors', 'N/A')}")
            print(f"AI Sizes: {ai_data.get('Sizes/Ounce', 'N/A')}")
            print(f"AI Designs: {ai_data.get('Designs', 'N/A')}")
            print(f"AI Styles: {ai_data.get('Styles', 'N/A')}")
        
        print("-" * 50)
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    # Test URLs
    test_urls = [
        "https://oddmolly.com/products/garden-blouse-1",
        "https://www.nike.com/t/air-max-270-mens-shoes-KkLcGr",
        "https://www.apple.com/shop/buy-iphone/iphone-15-pro"
    ]
    
    print("PRODUCT EXTRACTION TEST")
    print("=" * 50)
    
    for url in test_urls:
        test_extraction(url)
        print()
