#!/usr/bin/env python3
"""
Zepto Browser Scraper
Uses OpenClaw browser tool to scrape live prices from Zepto
"""

import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "zepto" / "live_prices"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Food category URLs to scrape
CATEGORIES = [
    ("oil", "/cn/atta-rice-oil-dals/oil/cid/2f7190d0-7c40-458b-b450-9a1006db3d95/scid/2b5e863c-9497-46ae-a7e9-85f6ef7380da"),
    ("atta", "/cn/atta-rice-oil-dals/atta/cid/2f7190d0-7c40-458b-b450-9a1006db3d95/scid/15644eea-d781-4cdd-8d85-e63bd9706b96"),
    ("rice", "/cn/atta-rice-oil-dals/rice-more/cid/2f7190d0-7c40-458b-b450-9a1006db3d95/scid/9798b797-0db0-4b04-b198-31b0a5849318"),
    ("dals", "/cn/atta-rice-oil-dals/dals-pulses/cid/2f7190d0-7c40-458b-b450-9a1006db3d95/scid/59c951bd-4cb4-4659-9467-1e72a8f972d9"),
    ("ghee", "/cn/atta-rice-oil-dals/ghee/cid/2f7190d0-7c40-458b-b450-9a1006db3d95/scid/56c015a7-b283-4e7a-b3ba-0f76f4f181dc"),
    ("dairy", "/cn/dairy-bread-eggs/dairy-bread-eggs/cid/4b938e02-7bde-4479-bc0a-2b54cb6bd5f5/scid/22964a2b-0439-4236-9950-0d71b532b243"),
    ("breakfast", "/cn/breakfast-sauces/breakfast-sauces/cid/f804bccc-c565-4879-b6ab-1b964bb1ed41/scid/68922181-4e0e-4a6b-9862-cf1a02ba240e"),
    ("snacks", "/cn/munchies/munchies/cid/d2c2a144-43cd-43e5-b308-92628fa68596/scid/d648ea7c-18f0-4178-a202-4751811b086b"),
    ("biscuits", "/cn/biscuits/biscuits/cid/2552acf2-2f77-4714-adc8-e505de3985db/scid/3a10723e-ba14-4e5c-bdeb-a4dce2c1bec4"),
    ("tea_coffee", "/cn/tea-coffee-more/tea-coffee-more/cid/d7e98d87-6850-4cf9-a37c-e4fa34ae302c/scid/e6763c2d-0bf3-4332-82e4-0c8df1c94cad"),
    ("masala", "/cn/masala-dry-fruits-more/masala-dry-fruits-more/cid/0c2ccf87-e32c-4438-9560-8d9488fc73e0/scid/8b44cef2-1bab-407e-aadd-29254e6778fa"),
    ("fruits_veg", "/cn/fruits-vegetables/fruits-vegetables/cid/64374cfe-d06f-4a01-898e-c07c46462c36/scid/e78a8422-5f20-4e4b-9a9f-22a0e53962e3"),
]

JS_EXTRACT = '''() => {
    const products = [];
    document.querySelectorAll('a[href*="/pn/"]').forEach(el => {
        const text = el.textContent;
        const priceMatch = text.match(/₹(\\d+)/);
        const mrpMatch = text.match(/₹(\\d+)\\s*₹(\\d+)/);
        const img = el.querySelector('img');
        const nameMatch = img?.alt || text.split('ADD')[0].split('Notify')[0].trim().slice(0, 100);
        const sizeMatch = text.match(/(\\d+(?:\\.\\d+)?\\s*(?:kg|g|L|ml|pc|pcs|pack)[^\\s]*)/i);
        const ratingMatch = text.match(/(\\d\\.\\d)\\s*\\((\\d+(?:\\.\\d+)?k?)\\)/);
        const soldOut = text.includes('Sold out');
        if (priceMatch && nameMatch.length > 3) {
            products.push({
                name: nameMatch.trim(),
                url: el.href,
                price: mrpMatch ? parseInt(mrpMatch[1]) : parseInt(priceMatch[1]),
                mrp: mrpMatch ? parseInt(mrpMatch[2]) : null,
                size: sizeMatch ? sizeMatch[1] : null,
                rating: ratingMatch ? parseFloat(ratingMatch[1]) : null,
                reviews: ratingMatch ? ratingMatch[2] : null,
                in_stock: !soldOut
            });
        }
    });
    return products;
}'''

def run_openclaw_browser(action, **kwargs):
    """Run openclaw browser command and return result."""
    cmd = ["openclaw", "browser", f"--browser-profile", "chrome", "--json"]
    cmd.append(action)
    for k, v in kwargs.items():
        cmd.extend([f"--{k.replace('_', '-')}", str(v)])
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    return json.loads(result.stdout)


def scrape_category(name, path):
    """Scrape a single category."""
    url = f"https://www.zeptonow.com{path}"
    print(f"Scraping {name}: {url}")
    
    # Navigate
    nav = run_openclaw_browser("navigate", url=url)
    if not nav or not nav.get("ok"):
        print(f"  Failed to navigate")
        return []
    
    time.sleep(3)  # Wait for page load
    
    # Extract products
    result = run_openclaw_browser("evaluate", fn=JS_EXTRACT)
    if not result or not result.get("ok"):
        print(f"  Failed to extract")
        return []
    
    products = result.get("result", [])
    print(f"  Found {len(products)} products")
    return products


def main():
    all_products = {}
    
    for name, path in CATEGORIES:
        products = scrape_category(name, path)
        all_products[name] = products
        time.sleep(2)  # Be nice
    
    # Save results
    output = {
        "scraped_at": datetime.now().isoformat(),
        "source": "zepto.com",
        "location": "Koramangala, Bengaluru",  # Based on attached browser
        "categories": all_products,
        "total_products": sum(len(p) for p in all_products.values())
    }
    
    output_file = OUTPUT_DIR / f"prices_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved {output['total_products']} products to {output_file}")
    return output


if __name__ == "__main__":
    main()
