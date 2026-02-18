#!/usr/bin/env python3
"""
Zepto HTML Parser
Extracts product data from saved Zepto HTML pages (view-source format)
"""

import re
import json
import sys
from html import unescape
from pathlib import Path
from datetime import datetime

def parse_zepto_html(file_path: str) -> list[dict]:
    """
    Parse a saved Zepto HTML page and extract product data.
    
    Args:
        file_path: Path to the saved HTML file
        
    Returns:
        List of product dictionaries with name, packsize, mrp, selling_price, discount_pct
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = unescape(f.read())
    
    # Clean up escaped JSON
    content = content.replace('\\"', '"').replace('\\n', '\n').replace('\\/', '/')
    
    # Extract fields in order
    names = []
    mrps = []
    selling_prices = []
    packsizes = []
    variant_ids = []
    
    # Product names - filter to actual products
    PRODUCT_KEYWORDS = [
        'butter', 'spread', 'honey', 'oil', 'vinegar', 'sauce', 'jam', 'chutney', 
        'pickle', 'jaggery', 'ketchup', 'dip', 'mayo', 'mayonnaise', 'mustard',
        'syrup', 'muesli', 'oats', 'cereal', 'cornflakes', 'poha', 'upma',
        'pasta', 'noodles', 'vermicelli', 'rice', 'dal', 'lentil', 'beans',
        'chocolate', 'cocoa', 'coffee', 'tea', 'milk', 'cream', 'cheese',
        'paneer', 'tofu', 'yogurt', 'curd', 'lassi', 'buttermilk',
        'bread', 'roti', 'naan', 'paratha', 'biscuit', 'cookie',
        'chips', 'namkeen', 'snack', 'nuts', 'seeds', 'dried',
        'juice', 'drink', 'water', 'soda', 'energy',
        'masala', 'spice', 'salt', 'sugar', 'flour', 'atta',
        'ghee', 'cooking', 'olive', 'coconut', 'sunflower',
        'protein', 'whey', 'supplement', 'vitamin',
        'organic', 'natural', 'fresh', 'pure'
    ]
    
    for match in re.finditer(r'"name"\s*:\s*"([^"]{10,200})"', content):
        name = match.group(1)
        if any(kw in name.lower() for kw in PRODUCT_KEYWORDS):
            names.append(name)
    
    # Packsizes
    for match in re.finditer(r'"formattedPacksize"\s*:\s*"([^"]+)"', content):
        packsizes.append(match.group(1))
    
    # Variant IDs (for deduplication/matching)
    for match in re.finditer(r'"productVariant"\s*:\s*\{[^}]*"id"\s*:\s*"([^"]+)"', content):
        variant_ids.append(match.group(1))
    
    # Prices - MRP appears twice per product, so we dedupe
    mrp_raw = [int(m.group(1)) for m in re.finditer(r'"mrp"\s*:\s*(\d+)', content)]
    mrps = mrp_raw[::2]  # Every other one
    
    selling_prices = [int(m.group(1)) for m in re.finditer(r'"sellingPrice"\s*:\s*(\d+)', content)]
    
    # Build products from available data
    min_len = min(len(names), len(mrps), len(selling_prices), len(packsizes))
    
    products = []
    for i in range(min_len):
        mrp = mrps[i] / 100  # Convert from paise
        selling = selling_prices[i] / 100
        discount = round((1 - selling/mrp) * 100) if mrp > 0 else 0
        
        products.append({
            'name': names[i],
            'packsize': packsizes[i],
            'mrp': mrp,
            'selling_price': selling,
            'discount_pct': discount,
            'variant_id': variant_ids[i] if i < len(variant_ids) else None
        })
    
    return products


def save_products(products: list[dict], output_path: str):
    """Save products to JSON file with metadata."""
    data = {
        'extracted_at': datetime.now().isoformat(),
        'source': 'zepto_html_parser',
        'product_count': len(products),
        'products': products
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(products)} products to {output_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python zepto_html_parser.py <html_file> [output_json]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    products = parse_zepto_html(input_file)
    
    print(f"\n{'='*60}")
    print(f"Extracted {len(products)} products from {input_file}")
    print(f"{'='*60}\n")
    
    for p in products[:10]:
        print(f"₹{p['selling_price']:.0f} (MRP ₹{p['mrp']:.0f}, {p['discount_pct']}% off) | {p['packsize']} | {p['name'][:50]}")
    
    if len(products) > 10:
        print(f"\n... and {len(products) - 10} more products")
    
    if output_file:
        save_products(products, output_file)
    
    return products


if __name__ == '__main__':
    main()
