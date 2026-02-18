#!/usr/bin/env python3
"""
Zepto Nutrition Enricher - Curl-based
Extracts nutrition, ingredients, and FSSAI from Zepto product pages via curl.
No browser required!
"""

import re
import json
import subprocess
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Koramangala 4th Block store ID
STORE_ID = "9ed1ce59-1de4-4c66-8910-20fba5c55a91"

def fetch_product_page(url: str, retries: int = 2) -> Optional[str]:
    """Fetch product page HTML via curl."""
    cmd = [
        'curl', '-sL', url,
        '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        '-H', f'Cookie: storeId={STORE_ID}',
        '--compressed',
        '--max-time', '15'
    ]
    
    for attempt in range(retries):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if result.returncode == 0 and len(result.stdout) > 10000:
                return result.stdout
            time.sleep(1)
        except subprocess.TimeoutExpired:
            print(f"  Timeout on attempt {attempt + 1}")
            time.sleep(2)
        except Exception as e:
            print(f"  Error: {e}")
            time.sleep(1)
    return None


def extract_nutrition(content: str) -> dict:
    """Extract nutrition data from HTML content."""
    # Decode Next.js escaped content
    content = content.replace('\\n', '\n').replace('\\"', '"').replace('\\/', '/')
    
    nutrition = {}
    
    # FSSAI format patterns: "Energy (kcal) 724"
    patterns = [
        (r'Energy \(kcal\) ([0-9.]+)', 'energy_kcal'),
        (r'Protein \(g\) ([0-9.]+)', 'protein_g'),
        (r'Carbohydrate \(g\) ([0-9.]+)', 'carbs_g'),
        (r'Total Fat \(g\) ([0-9.]+)', 'fat_g'),
        (r'Total Sugars \(g\) ([0-9.]+)', 'sugar_g'),
        (r'Added Sugars \(g\) ([0-9.]+)', 'added_sugar_g'),
        (r'Dietary Fibre \(g\) ([0-9.]+)', 'fiber_g'),
        (r'Sodium \(mg\) ([0-9.]+)', 'sodium_mg'),
        (r'Saturated Fat \(g\) ([0-9.]+)', 'saturated_fat_g'),
        (r'Trans Fat \(g\) ([0-9.]+)', 'trans_fat_g'),
    ]
    
    for pattern, key in patterns:
        match = re.search(pattern, content)
        if match:
            nutrition[key] = float(match.group(1))
    
    return nutrition


def extract_ingredients(content: str) -> Optional[str]:
    """Extract ingredients from HTML content."""
    content = content.replace('\\n', '\n').replace('\\"', '"').replace('\\/', '/')
    
    # Try various patterns for ingredients
    patterns = [
        r'"ingredients"\s*:\s*"([^"]{10,})"',
        r'"Ingredients"\s*:\s*"([^"]{10,})"',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            ingredients = match.group(1)
            # Clean up the ingredients text
            ingredients = ingredients.replace('\\n', ' ').replace('\\', '').strip()
            return ingredients
    
    return None


def extract_fssai(content: str) -> Optional[str]:
    """Extract FSSAI license number from HTML content."""
    content = content.replace('\\n', '\n').replace('\\"', '"').replace('\\/', '/')
    
    patterns = [
        r'"fssaiLicense"\s*:\s*"([^"]+)"',
        r'"fssaiLicenseNo"\s*:\s*"([^"]+)"',
        r'FSSAI[^0-9]*([0-9]{12,14})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def extract_product_info(content: str, product_name: str, pvid: str) -> dict:
    """Extract all product information from HTML."""
    nutrition = extract_nutrition(content)
    ingredients = extract_ingredients(content)
    fssai = extract_fssai(content)
    
    # Check if it's a real 404 - no nutrition data AND has 404 marker
    has_404_marker = 'NEXT_HTTP_ERROR_FALLBACK;404' in content or 'page you\'re looking for' in content
    is_404 = has_404_marker and len(nutrition) == 0 and not ingredients
    
    return {
        "pvid": pvid,
        "name": product_name,
        "nutrition": nutrition if nutrition else None,
        "ingredients": ingredients,
        "fssai": fssai,
        "has_nutrition": len(nutrition) > 0,
        "is_404": is_404,
        "scraped_at": datetime.now().isoformat()
    }


def enrich_product(name: str, pvid: str, url: str = None) -> dict:
    """Fetch and enrich a single product."""
    if not url:
        # Construct URL from pvid
        slug = name.lower().replace(' ', '-').replace('(', '').replace(')', '').replace(',', '')
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        slug = re.sub(r'-+', '-', slug).strip('-')
        url = f"https://www.zeptonow.com/pn/{slug}/pvid/{pvid}"
    
    print(f"  Fetching: {name[:40]}...")
    html = fetch_product_page(url)
    
    if not html:
        return {
            "pvid": pvid,
            "name": name,
            "error": "fetch_failed",
            "scraped_at": datetime.now().isoformat()
        }
    
    info = extract_product_info(html, name, pvid)
    
    if info['is_404']:
        print(f"    ⚠️  404 - Product not found")
    elif info['has_nutrition']:
        print(f"    ✓ Nutrition: {len(info['nutrition'])} fields")
    else:
        print(f"    - No nutrition data")
    
    return info


def batch_enrich(products: list, output_dir: str, batch_size: int = 50, delay: float = 0.5):
    """Enrich a batch of products."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    results = []
    success_count = 0
    error_count = 0
    
    for i, product in enumerate(products):
        name = product.get('name', 'Unknown')
        pvid = product.get('pvid')
        url = product.get('url')
        
        if not pvid:
            print(f"[{i+1}/{len(products)}] Skipping {name} - no pvid")
            continue
        
        print(f"[{i+1}/{len(products)}]", end="")
        result = enrich_product(name, pvid, url)
        results.append(result)
        
        if result.get('has_nutrition'):
            success_count += 1
        elif result.get('error') or result.get('is_404'):
            error_count += 1
        
        # Save intermediate results every batch_size products
        if (i + 1) % batch_size == 0:
            save_results(results, output_path, f"batch_{(i+1)//batch_size}")
        
        time.sleep(delay)
    
    # Save final results
    save_results(results, output_path, "final")
    
    print(f"\n=== Summary ===")
    print(f"Total: {len(products)}")
    print(f"With nutrition: {success_count}")
    print(f"Errors/404s: {error_count}")
    print(f"No nutrition: {len(products) - success_count - error_count}")
    
    return results


def save_results(results: list, output_path: Path, suffix: str):
    """Save results to JSON file."""
    filename = output_path / f"nutrition_enriched_{suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump({
            "extracted_at": datetime.now().isoformat(),
            "count": len(results),
            "with_nutrition": sum(1 for r in results if r.get('has_nutrition')),
            "products": results
        }, f, indent=2)
    print(f"  Saved: {filename}")


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description='Zepto Nutrition Enricher (curl-based)')
    parser.add_argument('--input', '-i', required=True, help='Input JSON file with products')
    parser.add_argument('--output', '-o', default='data/zepto/nutrition_curl/', help='Output directory')
    parser.add_argument('--limit', '-l', type=int, help='Limit number of products to process')
    parser.add_argument('--delay', '-d', type=float, default=0.5, help='Delay between requests')
    parser.add_argument('--test', '-t', action='store_true', help='Test mode - process first 5')
    
    args = parser.parse_args()
    
    # Load products
    with open(args.input) as f:
        data = json.load(f)
    
    if isinstance(data, dict) and 'products' in data:
        products = data['products']
    elif isinstance(data, list):
        products = data
    else:
        print("Error: Could not find products in input file")
        sys.exit(1)
    
    # Filter to products with pvids
    products = [p for p in products if p.get('pvid')]
    print(f"Found {len(products)} products with pvids")
    
    if args.test:
        products = products[:5]
        print("Test mode: processing first 5")
    elif args.limit:
        products = products[:args.limit]
        print(f"Processing first {args.limit}")
    
    batch_enrich(products, args.output, delay=args.delay)


if __name__ == '__main__':
    main()
