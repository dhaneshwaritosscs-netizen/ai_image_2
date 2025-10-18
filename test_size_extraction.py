#!/usr/bin/env python3
"""
Test script specifically for size extraction
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from urllib.parse import urlparse

def test_size_extraction(url):
    """Test size extraction on a sample URL"""
    print(f"Testing SIZE EXTRACTION for: {url}")
    print("-" * 60)
    
    try:
        # Import the extraction function
        from app import extract_product_data
        
        # Extract data
        result = extract_product_data(url)
        
        if 'error' in result:
            print(f"ERROR: {result['error']}")
            return
        
        # Display basic results
        print("BASIC EXTRACTION RESULTS:")
        print("-" * 30)
        print(f"Product Name: {result.get('name', 'N/A')}")
        print(f"Brand: {result.get('brand', 'N/A')}")
        print(f"Price: {result.get('price', 'N/A')}")
        print(f"SKU: {result.get('sku', 'N/A')}")
        
        # Focus on size extraction
        print("\nSIZE EXTRACTION RESULTS:")
        print("-" * 30)
        
        if result.get('size_chart'):
            print(f"✅ Sizes found: {len(result['size_chart'])}")
            for i, size_info in enumerate(result['size_chart']):
                size = size_info.get('size', 'N/A')
                availability = size_info.get('availability', 'N/A')
                print(f"  {i+1}. Size: {size} | Availability: {availability}")
        else:
            print("❌ No sizes found")
        
        # Check AI extracted sizes
        if result.get('ai_extracted'):
            ai_sizes = result['ai_extracted'].get('Sizes/Ounce', 'N/A')
            print(f"\nAI Extracted Sizes: {ai_sizes}")
        
        # Display images count
        if result.get('images'):
            print(f"\nImages found: {len(result['images'])}")
        
        print("-" * 60)
        
    except Exception as e:
        print(f"ERROR: {e}")

def test_multiple_sites():
    """Test size extraction on multiple e-commerce sites"""
    test_urls = [
        "https://oddmolly.com/products/garden-blouse-1",
        "https://www.nike.com/t/air-max-270-mens-shoes-KkLcGr",
        "https://www.zara.com/us/en/woman/t-shirts-c358002.html",
        "https://www.hm.com/us/en/productpage.0985055001.html",
        "https://www.levi.com/US/en_US/clothing/men/jeans/501-original-fit-jeans/p/5010000001"
    ]
    
    print("COMPREHENSIVE SIZE EXTRACTION TEST")
    print("=" * 60)
    
    for i, url in enumerate(test_urls):
        print(f"\nTEST {i+1}/{len(test_urls)}")
        test_size_extraction(url)
        print()

if __name__ == "__main__":
    # Test single URL
    test_url = "https://oddmolly.com/products/garden-blouse-1"
    test_size_extraction(test_url)
    
    # Uncomment to test multiple sites
    # test_multiple_sites()
