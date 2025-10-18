import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin

def extract_cashott_product_data(url):
    """
    Extract product data from Cashott website
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract product information
        product_data = {}
        
        # Product name
        product_name = soup.find('h1')
        if product_name:
            product_data['name'] = product_name.get_text().strip()
        
        # Price - look for structured data first
        price = None
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'offers' in data:
                    offers = data['offers']
                    if isinstance(offers, list) and len(offers) > 0:
                        price = offers[0].get('price')
                        break
            except:
                continue
        
        if price:
            product_data['price'] = f"€{price}"
        else:
            # Fallback to text search
            price_element = soup.find('span', class_='price')
            if price_element:
                product_data['price'] = price_element.get_text().strip()
        
        # Extract structured data from JSON-LD
        structured_data = None
        for script in script_tags:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'name' in data:
                    structured_data = data
                    break
            except:
                continue
        
        if structured_data:
            # Extract detailed information from structured data
            product_data['brand'] = structured_data.get('brand', 'CASHOTT')
            product_data['sku'] = structured_data.get('sku', '')
            product_data['gtin13'] = structured_data.get('gtin13', '')
            
            # Extract offers (sizes and availability)
            offers = structured_data.get('offers', [])
            size_variants = []
            for offer in offers:
                if isinstance(offer, dict):
                    sku = offer.get('sku', '')
                    if '\\' in sku:
                        size = sku.split('\\')[-1]
                        availability = offer.get('availability', '')
                        price = offer.get('price', 0)
                        
                        size_variants.append({
                            'size': size,
                            'price': f"€{price}",
                            'availability': 'In Stock' if 'InStock' in availability else 'Out of Stock',
                            'sku': sku
                        })
            
            product_data['size_variants'] = size_variants
            
            # Extract description
            description = structured_data.get('description', '')
            if description:
                # Clean up the description
                desc_parts = description.split('Style no.')
                if len(desc_parts) > 1:
                    main_desc = desc_parts[0].strip()
                    style_info = 'Style no.' + desc_parts[1].strip()
                    
                    # Parse materials and specifications
                    materials = []
                    specifications = []
                    
                    if 'Materials:' in main_desc:
                        materials_section = main_desc.split('Materials:')[1].split('Specifications:')[0]
                        materials = [m.strip() for m in materials_section.split('-') if m.strip()]
                    
                    if 'Specifications:' in main_desc:
                        specs_section = main_desc.split('Specifications:')[1]
                        specifications = [s.strip() for s in specs_section.split('-') if s.strip()]
                    
                    product_data['materials'] = materials
                    product_data['specifications'] = specifications
                    product_data['description'] = main_desc.split('Materials:')[0].strip()
                    product_data['style_info'] = style_info
        
        # Size chart
        size_table = soup.find('table')
        if size_table:
            sizes = []
            rows = size_table.find_all('tr')
            for row in rows[1:]:  # Skip header row
                cells = row.find_all('td')
                if len(cells) >= 2:
                    size_info = {
                        'size': cells[0].get_text().strip(),
                        'foot_length_cm': cells[1].get_text().strip()
                    }
                    sizes.append(size_info)
            product_data['size_chart'] = sizes
        
        # Images
        images = []
        if structured_data and 'image' in structured_data:
            img_data = structured_data['image']
            if isinstance(img_data, dict):
                images.append(img_data.get('url', ''))
            elif isinstance(img_data, str):
                images.append(img_data)
        
        # Also get additional images from img tags
        img_tags = soup.find_all('img')
        for img in img_tags:
            src = img.get('src')
            if src and 'CASDIANA' in src:
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = urljoin(url, src)
                if src not in images:
                    images.append(src)
        
        product_data['images'] = images
        
        # Additional product details
        product_data['url'] = url
        
        return product_data
        
    except requests.RequestException as e:
        print(f"Error fetching the webpage: {e}")
        return None
    except Exception as e:
        print(f"Error parsing the webpage: {e}")
        return None

def save_to_json(data, filename='cashott_product_data_clean.json'):
    """Save extracted data to JSON file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Data saved to {filename}")
    except Exception as e:
        print(f"Error saving data: {e}")

if __name__ == "__main__":
    url = "https://cashott.com/products/casdiana-mary-jane-patent-red?_pos=1&_sid=08a65f3cb&_ss=r"
    
    print("Extracting product data from Cashott website...")
    product_data = extract_cashott_product_data(url)
    
    if product_data:
        print("\nExtracted Product Data:")
        print("=" * 50)
        for key, value in product_data.items():
            if key == 'size_variants':
                print(f"{key}:")
                for variant in value:
                    print(f"  - Size {variant['size']}: {variant['price']} ({variant['availability']})")
            elif key == 'images':
                print(f"{key}: {len(value)} images found")
                for i, img in enumerate(value[:3]):  # Show first 3 images
                    print(f"  {i+1}. {img}")
            else:
                print(f"{key}: {value}")
        
        # Save to JSON file
        save_to_json(product_data)
    else:
        print("Failed to extract product data")
