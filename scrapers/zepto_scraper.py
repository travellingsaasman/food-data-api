#!/usr/bin/env python3
"""
Zepto.com Product Data Scraper
Extracts product catalog from sitemaps for Indian Food Data API
"""

import requests
import xml.etree.ElementTree as ET
import json
import re
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, unquote

# Config
BASE_URL = "https://www.zepto.com"
SITEMAP_PRODUCTS = f"{BASE_URL}/sitemap/products.xml"
SITEMAP_CATEGORIES = f"{BASE_URL}/sitemap/categories.xml"
SITEMAP_BRANDS = f"{BASE_URL}/sitemap/brands.xml"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "zepto"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FoodDataAPI/1.0; +https://github.com/travellingsaasman)",
    "Accept": "application/xml,text/xml,*/*"
}

def fetch_xml(url: str) -> ET.Element:
    """Fetch and parse XML from URL"""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return ET.fromstring(resp.content)

def parse_sitemap_index(url: str) -> list[str]:
    """Parse sitemap index and return list of sitemap URLs"""
    root = fetch_xml(url)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [loc.text for loc in root.findall(".//sm:loc", ns)]

def parse_product_url(url: str) -> dict:
    """Extract product info from URL pattern:
    https://www.zepto.com/pn/{slug}/pvid/{product_variant_id}
    """
    match = re.match(r".*/pn/([^/]+)/pvid/([a-f0-9-]+)", url)
    if not match:
        return None
    
    slug = match.group(1)
    pvid = match.group(2)
    
    # Parse slug to extract product name and possible attributes
    name_parts = slug.replace("-", " ").split()
    
    # Try to extract weight/quantity patterns
    weight_pattern = r"(\d+(?:\.\d+)?)\s*(kg|g|ml|l|litre|liter|gm|gram|pack|piece|pc|count|unit)"
    weight_match = re.search(weight_pattern, slug.replace("-", " "), re.I)
    
    return {
        "product_variant_id": pvid,
        "slug": slug,
        "name": unquote(slug.replace("-", " ")).title(),
        "url": url,
        "weight": weight_match.group(0) if weight_match else None
    }

def parse_category_url(url: str) -> dict:
    """Extract category info from URL pattern:
    https://www.zepto.com/cn/{category}/{subcategory}/cid/{cat_id}/scid/{subcat_id}
    """
    match = re.match(r".*/cn/([^/]+)/([^/]+)/cid/([a-f0-9-]+)/scid/([a-f0-9-]+)", url)
    if not match:
        return None
    
    return {
        "category_slug": match.group(1),
        "subcategory_slug": match.group(2),
        "category_id": match.group(3),
        "subcategory_id": match.group(4),
        "category_name": match.group(1).replace("-", " ").title(),
        "subcategory_name": match.group(2).replace("-", " ").title(),
        "url": url
    }

def parse_brand_url(url: str) -> dict:
    """Extract brand info from URL pattern:
    https://www.zepto.com/brand/{brand_name}/{brand_id}
    """
    match = re.match(r".*/brand/([^/]+)/([a-f0-9-]+)", url)
    if not match:
        return None
    
    return {
        "brand_slug": match.group(1),
        "brand_id": match.group(2),
        "brand_name": unquote(match.group(1).replace("_", " ")).replace("'S", "'s"),
        "url": url
    }

def scrape_products_sitemap(sitemap_url: str) -> list[dict]:
    """Scrape a single products sitemap"""
    products = []
    try:
        root = fetch_xml(sitemap_url)
        ns = {
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "image": "http://www.google.com/schemas/sitemap-image/1.1"
        }
        
        for url_elem in root.findall(".//sm:url", ns):
            loc = url_elem.find("sm:loc", ns)
            if loc is None:
                continue
            
            product = parse_product_url(loc.text)
            if not product:
                continue
            
            # Get image
            img_loc = url_elem.find(".//image:loc", ns)
            img_title = url_elem.find(".//image:title", ns)
            if img_loc is not None:
                product["image_url"] = img_loc.text
            if img_title is not None:
                product["image_title"] = img_title.text
            
            # Get lastmod
            lastmod = url_elem.find("sm:lastmod", ns)
            if lastmod is not None:
                product["last_modified"] = lastmod.text
            
            products.append(product)
    except Exception as e:
        print(f"Error scraping {sitemap_url}: {e}")
    
    return products

def scrape_categories() -> list[dict]:
    """Scrape all categories from sitemap"""
    categories = []
    try:
        root = fetch_xml(SITEMAP_CATEGORIES)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        
        for loc in root.findall(".//sm:loc", ns):
            cat = parse_category_url(loc.text)
            if cat:
                categories.append(cat)
    except Exception as e:
        print(f"Error scraping categories: {e}")
    
    return categories

def scrape_brands() -> list[dict]:
    """Scrape all brands from sitemap"""
    brands = []
    try:
        root = fetch_xml(SITEMAP_BRANDS)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        
        for loc in root.findall(".//sm:loc", ns):
            brand = parse_brand_url(loc.text)
            if brand:
                brands.append(brand)
    except Exception as e:
        print(f"Error scraping brands: {e}")
    
    return brands

def main():
    """Main scraper entry point"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"[{datetime.now()}] Starting Zepto scraper...")
    
    # 1. Scrape categories
    print("Scraping categories...")
    categories = scrape_categories()
    with open(OUTPUT_DIR / "categories.json", "w") as f:
        json.dump({"count": len(categories), "categories": categories}, f, indent=2)
    print(f"  → {len(categories)} categories")
    
    # 2. Scrape brands
    print("Scraping brands...")
    brands = scrape_brands()
    with open(OUTPUT_DIR / "brands.json", "w") as f:
        json.dump({"count": len(brands), "brands": brands}, f, indent=2)
    print(f"  → {len(brands)} brands")
    
    # 3. Get list of product sitemaps
    print("Getting product sitemap index...")
    product_sitemaps = parse_sitemap_index(SITEMAP_PRODUCTS)
    print(f"  → {len(product_sitemaps)} product sitemaps")
    
    # 4. Scrape all product sitemaps (parallel)
    print("Scraping products (parallel)...")
    all_products = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(scrape_products_sitemap, url): url for url in product_sitemaps}
        for i, future in enumerate(as_completed(futures)):
            url = futures[future]
            try:
                products = future.result()
                all_products.extend(products)
                print(f"  → [{i+1}/{len(product_sitemaps)}] {len(products)} products from {url.split('/')[-1]}")
            except Exception as e:
                print(f"  → Error with {url}: {e}")
            time.sleep(0.5)  # Rate limiting
    
    # 5. Save products
    with open(OUTPUT_DIR / "products.json", "w") as f:
        json.dump({
            "count": len(all_products),
            "scraped_at": datetime.now().isoformat(),
            "products": all_products
        }, f, indent=2)
    
    # 6. Summary
    print(f"\n[{datetime.now()}] Scraping complete!")
    print(f"  Categories: {len(categories)}")
    print(f"  Brands: {len(brands)}")
    print(f"  Products: {len(all_products)}")
    print(f"  Output: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
