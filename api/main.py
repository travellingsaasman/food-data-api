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


# Price data storage (in-memory, can be persisted)
PRICE_DATA = {}
PRICE_DATA_FILE = DATA_DIR / "prices.json"

# Load existing price data if available
if PRICE_DATA_FILE.exists():
    with open(PRICE_DATA_FILE) as f:
        PRICE_DATA = json.load(f)


@app.post("/prices/ingest")
def ingest_prices(data: dict):
    """
    Ingest price data from HTML parser output.
    
    Expected format:
    {
        "products": [
            {
                "name": "Product Name",
                "packsize": "1 pc (250 g)",
                "mrp": 425.0,
                "selling_price": 416.0,
                "discount_pct": 2,
                "variant_id": "uuid"
            }
        ],
        "source": "zepto",
        "location": "Koramangala 4th Block, Bengaluru"
    }
    """
    from datetime import datetime
    
    products = data.get('products', [])
    source = data.get('source', 'unknown')
    location = data.get('location', 'unknown')
    timestamp = datetime.now().isoformat()
    
    ingested = 0
    for p in products:
        key = f"{source}:{p.get('variant_id') or p.get('name')}"
        
        # Store price data with history
        if key not in PRICE_DATA:
            PRICE_DATA[key] = {
                'name': p['name'],
                'packsize': p.get('packsize'),
                'source': source,
                'price_history': []
            }
        
        PRICE_DATA[key]['price_history'].append({
            'mrp': p.get('mrp'),
            'selling_price': p.get('selling_price'),
            'discount_pct': p.get('discount_pct'),
            'location': location,
            'timestamp': timestamp
        })
        
        # Keep only last 100 price points
        PRICE_DATA[key]['price_history'] = PRICE_DATA[key]['price_history'][-100:]
        ingested += 1
    
    # Persist to file
    with open(PRICE_DATA_FILE, 'w') as f:
        json.dump(PRICE_DATA, f, indent=2)
    
    return {
        'status': 'success',
        'ingested': ingested,
        'total_tracked': len(PRICE_DATA),
        'timestamp': timestamp
    }


@app.get("/prices")
def get_prices(
    q: Optional[str] = Query(None, description="Search by product name"),
    source: Optional[str] = Query(None, description="Filter by source (zepto, blinkit, etc)"),
    limit: int = Query(50, ge=1, le=500),
):
    """Get tracked prices with history"""
    results = []
    
    for key, data in PRICE_DATA.items():
        if q and q.lower() not in data['name'].lower():
            continue
        if source and source.lower() not in data['source'].lower():
            continue
        
        latest = data['price_history'][-1] if data['price_history'] else {}
        results.append({
            'key': key,
            'name': data['name'],
            'packsize': data.get('packsize'),
            'source': data['source'],
            'current_price': latest.get('selling_price'),
            'mrp': latest.get('mrp'),
            'discount_pct': latest.get('discount_pct'),
            'last_updated': latest.get('timestamp'),
            'price_points': len(data['price_history'])
        })
    
    return {
        'total': len(results),
        'results': results[:limit]
    }


@app.get("/prices/{key}")
def get_price_history(key: str):
    """Get full price history for a product"""
    # URL decode the key
    from urllib.parse import unquote
    key = unquote(key)
    
    if key not in PRICE_DATA:
        raise HTTPException(status_code=404, detail="Product not tracked")
    
    return PRICE_DATA[key]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
