#!/usr/bin/env python3
"""
Indian Food Data API
Built from Zepto.com product catalog
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
from pathlib import Path
from typing import Optional
import re

# Load data
DATA_DIR = Path(__file__).parent.parent / "data" / "zepto"

with open(DATA_DIR / "products_food.json") as f:
    PRODUCTS_DATA = json.load(f)
    PRODUCTS = PRODUCTS_DATA['products']

with open(DATA_DIR / "categories.json") as f:
    CATEGORIES = json.load(f)['categories']

with open(DATA_DIR / "brands.json") as f:
    BRANDS = json.load(f)['brands']

# Build indices
PRODUCTS_BY_ID = {p['product_variant_id']: p for p in PRODUCTS}
BRANDS_BY_ID = {b['brand_id']: b for b in BRANDS}
BRANDS_BY_SLUG = {b['brand_slug'].lower(): b for b in BRANDS}

# Extract unique category slugs
FOOD_CATEGORIES = list(set(c['category_slug'] for c in CATEGORIES if any(x in c['category_slug'].lower() for x in [
    'atta', 'rice', 'oil', 'dal', 'dairy', 'bread', 'egg', 'fruit', 'vegetable',
    'masala', 'meat', 'fish', 'frozen', 'breakfast', 'snack', 'biscuit',
    'chocolate', 'sweet', 'tea', 'coffee', 'juice', 'drink', 'ice-cream', 'packaged'
])))

app = FastAPI(
    title="Indian Food Data API",
    description="Product catalog from Indian grocery platforms (Zepto)",
    version="0.1.0",
    docs_url="/",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/stats")
def get_stats():
    """Get catalog statistics"""
    return {
        "total_products": len(PRODUCTS),
        "total_brands": len(BRANDS),
        "total_categories": len(CATEGORIES),
        "food_categories": len(FOOD_CATEGORIES),
        "products_with_weight": sum(1 for p in PRODUCTS if p.get('weight')),
        "source": "zepto.com",
        "scraped_at": PRODUCTS_DATA.get('scraped_at'),
    }


@app.get("/products")
def list_products(
    q: Optional[str] = Query(None, description="Search query"),
    brand: Optional[str] = Query(None, description="Filter by brand slug"),
    category: Optional[str] = Query(None, description="Filter by category keyword"),
    has_weight: Optional[bool] = Query(None, description="Only products with weight info"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List/search products"""
    results = PRODUCTS
    
    # Search
    if q:
        q_lower = q.lower()
        results = [p for p in results if q_lower in p['name'].lower() or q_lower in p['slug'].lower()]
    
    # Brand filter
    if brand:
        brand_lower = brand.lower()
        results = [p for p in results if brand_lower in p['slug'].lower()]
    
    # Category filter (keyword match on slug)
    if category:
        cat_lower = category.lower()
        results = [p for p in results if cat_lower in p['slug'].lower()]
    
    # Weight filter
    if has_weight:
        results = [p for p in results if p.get('weight')]
    
    total = len(results)
    results = results[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": results,
    }


@app.get("/products/{product_id}")
def get_product(product_id: str):
    """Get product by ID"""
    product = PRODUCTS_BY_ID.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/brands")
def list_brands(
    q: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List/search brands"""
    results = BRANDS
    
    if q:
        q_lower = q.lower()
        results = [b for b in results if q_lower in b['brand_name'].lower()]
    
    total = len(results)
    results = results[offset:offset + limit]
    
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": results,
    }


@app.get("/brands/{brand_id}")
def get_brand(brand_id: str):
    """Get brand by ID"""
    brand = BRANDS_BY_ID.get(brand_id)
    if not brand:
        # Try slug
        brand = BRANDS_BY_SLUG.get(brand_id.lower())
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Get products for brand
    products = [p for p in PRODUCTS if brand['brand_slug'].lower() in p['slug'].lower()][:20]
    
    return {
        **brand,
        "product_count": len([p for p in PRODUCTS if brand['brand_slug'].lower() in p['slug'].lower()]),
        "sample_products": products,
    }


@app.get("/categories")
def list_categories():
    """List all food categories"""
    # Group by category
    grouped = {}
    for cat in CATEGORIES:
        slug = cat['category_slug']
        if slug not in grouped:
            grouped[slug] = {
                "category_slug": slug,
                "category_name": cat['category_name'],
                "category_id": cat['category_id'],
                "subcategories": []
            }
        grouped[slug]['subcategories'].append({
            "subcategory_slug": cat['subcategory_slug'],
            "subcategory_name": cat['subcategory_name'],
            "subcategory_id": cat['subcategory_id'],
        })
    
    return {"categories": list(grouped.values())}


@app.get("/search/advanced")
def advanced_search(
    name: Optional[str] = Query(None, description="Product name contains"),
    weight_min: Optional[float] = Query(None, description="Minimum weight in grams"),
    weight_max: Optional[float] = Query(None, description="Maximum weight in grams"),
    brand: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    """Advanced search with weight parsing"""
    results = PRODUCTS
    
    if name:
        name_lower = name.lower()
        results = [p for p in results if name_lower in p['name'].lower()]
    
    if brand:
        brand_lower = brand.lower()
        results = [p for p in results if brand_lower in p['slug'].lower()]
    
    # Weight filtering (parse weight strings)
    if weight_min or weight_max:
        def parse_weight_grams(w):
            if not w:
                return None
            w = w.lower()
            match = re.match(r'([\d.]+)\s*(kg|g|gm|gram|ml|l|litre)', w)
            if not match:
                return None
            val = float(match.group(1))
            unit = match.group(2)
            if unit == 'kg':
                return val * 1000
            elif unit in ('l', 'litre'):
                return val * 1000  # ml
            return val
        
        filtered = []
        for p in results:
            grams = parse_weight_grams(p.get('weight'))
            if grams is None:
                continue
            if weight_min and grams < weight_min:
                continue
            if weight_max and grams > weight_max:
                continue
            filtered.append({**p, 'weight_grams': grams})
        results = filtered
    
    return {
        "total": len(results),
        "results": results[:limit],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
