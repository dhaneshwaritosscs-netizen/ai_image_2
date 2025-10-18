#!/usr/bin/env python3
"""
Simple test script for product data extraction (without AI model)
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urlparse

def test_extraction_simple(url):
    """Test the extraction on a sample URL without AI model"""
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
        
        # Display images
        if result.get('images'):
            print(f"Images found: {len(result['images'])}")
        
        print("-" * 50)
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    # Test URLs
    test_urls = [
        "https://oddmolly.com/products/garden-blouse-1",
    ]
    
    print("SIMPLE PRODUCT EXTRACTION TEST (No AI Model)")
    print("=" * 50)
    
    for url in test_urls:
        test_extraction_simple(url)
        print()
