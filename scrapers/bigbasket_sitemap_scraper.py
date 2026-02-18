#!/usr/bin/env python3
"""
BigBasket Sitemap Scraper
Fetches product catalog from BigBasket's XML sitemaps
"""

import requests
import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import time

SITEMAP_INDEX = "https://www.bigbasket.com/sitemap.xml"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "bigbasket"

# XML namespaces
NS = {
    'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
    'image': 'http://www.google.com/schemas/sitemap-image/1.1'
}


def fetch_sitemap(url: str) -> str:
    """Fetch sitemap XML."""
    print(f"Fetching: {url}")
    resp = requests.get(url, timeout=60, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; FoodDataBot/1.0)'
    })
    resp.raise_for_status()
    return resp.text


def parse_sitemap_index(xml_content: str) -> list[str]:
    """Parse sitemap index to get product sitemap URLs."""
    root = ET.fromstring(xml_content)
    sitemaps = []
    for sitemap in root.findall('.//sm:sitemap', NS):
        loc = sitemap.find('sm:loc', NS)
        if loc is not None and 'productsitemap' in loc.text:
            sitemaps.append(loc.text)
    return sitemaps


def parse_product_sitemap(xml_content: str) -> list[dict]:
    """Parse product sitemap and extract product info."""
    root = ET.fromstring(xml_content)
    products = []
    
    for url in root.findall('.//sm:url', NS):
        loc = url.find('sm:loc', NS)
        image = url.find('.//image:image', NS)
        
        if loc is None:
            continue
            
        product_url = loc.text
        
        # Extract product ID and slug from URL
        # Format: /pd/{id}/{slug}/
        match = re.search(r'/pd/(\d+)/([^/]+)/', product_url)
        if not match:
            continue
            
        product_id = match.group(1)
        slug = match.group(2)
        
        # Get image info
        image_url = None
        title = None
        if image is not None:
            img_loc = image.find('image:loc', NS)
            img_title = image.find('image:title', NS)
            if img_loc is not None:
                image_url = img_loc.text
            if img_title is not None:
                title = img_title.text
        
        # Parse weight from title
        weight = None
        if title:
            # Patterns: "500 g", "1 kg", "250 ml", "1 L", etc.
            weight_match = re.search(r'(\d+(?:\.\d+)?)\s*(g|gm|kg|ml|l|litre|ltr|pcs?|pack)\b', title, re.I)
            if weight_match:
                weight = f"{weight_match.group(1)} {weight_match.group(2)}"
        
        # Parse brand from slug (first word usually)
        brand = slug.split('-')[0] if slug else None
        
        products.append({
            'product_id': product_id,
            'slug': slug,
            'url': product_url,
            'name': title,
            'image_url': image_url,
            'weight': weight,
            'brand_hint': brand
        })
    
    return products


def scrape_all_products():
    """Scrape all products from BigBasket sitemaps."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Fetch sitemap index
    index_xml = fetch_sitemap(SITEMAP_INDEX)
    product_sitemaps = parse_sitemap_index(index_xml)
    
    print(f"Found {len(product_sitemaps)} product sitemaps")
    
    all_products = []
    
    for sitemap_url in product_sitemaps:
        try:
            xml_content = fetch_sitemap(sitemap_url)
            products = parse_product_sitemap(xml_content)
            all_products.extend(products)
            print(f"  Extracted {len(products)} products (total: {len(all_products)})")
            time.sleep(0.5)  # Be nice
        except Exception as e:
            print(f"  Error: {e}")
    
    # Save all products
    output = {
        'scraped_at': datetime.now().isoformat(),
        'source': 'bigbasket.com',
        'total_products': len(all_products),
        'products': all_products
    }
    
    output_file = OUTPUT_DIR / 'products_all.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved {len(all_products)} products to {output_file}")
    
    # Also save a smaller food-only version
    FOOD_KEYWORDS = [
        'rice', 'dal', 'atta', 'oil', 'ghee', 'sugar', 'salt', 'masala', 'spice',
        'milk', 'curd', 'paneer', 'cheese', 'butter', 'cream',
        'bread', 'biscuit', 'cookie', 'cake', 'chips', 'namkeen',
        'tea', 'coffee', 'juice', 'drink', 'water',
        'fruit', 'vegetable', 'egg', 'meat', 'fish', 'chicken',
        'honey', 'jam', 'sauce', 'ketchup', 'pickle', 'chutney',
        'noodle', 'pasta', 'oats', 'cereal', 'muesli',
        'chocolate', 'sweet', 'candy', 'dry-fruit', 'nut'
    ]
    
    food_products = [
        p for p in all_products 
        if p.get('slug') and any(kw in p['slug'].lower() for kw in FOOD_KEYWORDS)
    ]
    
    food_output = {
        'scraped_at': datetime.now().isoformat(),
        'source': 'bigbasket.com',
        'total_products': len(food_products),
        'products': food_products
    }
    
    food_file = OUTPUT_DIR / 'products_food.json'
    with open(food_file, 'w', encoding='utf-8') as f:
        json.dump(food_output, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(food_products)} food products to {food_file}")
    
    return all_products


if __name__ == '__main__':
    scrape_all_products()
