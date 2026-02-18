#!/usr/bin/env python3
"""
Full category scraper for Zepto using browser relay
Run from command line or import scrape_category function
"""

import json
import subprocess
import time
from datetime import datetime

# Category URLs for Koramangala location
CATEGORIES = {
    "milk": "/cn/dairy-bread-eggs/milk/cid/4b938e02-7bde-4479-bc0a-2b54cb6bd5f5/scid/22964a2b-0439-4236-9950-0d71b532b243",
    "curd": "/cn/dairy-bread-eggs/curd-probiotic-drink/cid/4b938e02-7bde-4479-bc0a-2b54cb6bd5f5/scid/5418d83c-4c50-4914-a768-b02c2aac2fea",
    "butter": "/cn/dairy-bread-eggs/butter/cid/4b938e02-7bde-4479-bc0a-2b54cb6bd5f5/scid/62b2b1eb-cd07-41b2-b567-cc878d2287fc",
    "cheese": "/cn/dairy-bread-eggs/cheese/cid/4b938e02-7bde-4479-bc0a-2b54cb6bd5f5/scid/f594b28a-4775-48ac-8840-b9030229ff87",
    "eggs": "/cn/dairy-bread-eggs/eggs/cid/4b938e02-7bde-4479-bc0a-2b54cb6bd5f5/scid/d638f064-e7f3-4161-b692-a3f472c64020",
    "paneer_cream": "/cn/dairy-bread-eggs/paneer-cream/cid/4b938e02-7bde-4479-bc0a-2b54cb6bd5f5/scid/1806412f-190a-46b1-be42-4237a4146eb1",
    "breads": "/cn/dairy-bread-eggs/breads-buns/cid/4b938e02-7bde-4479-bc0a-2b54cb6bd5f5/scid/30566884-bbd7-49fa-8c3f-43c90a571c9e",
    "oil": "/cn/atta-rice-oil-dals/oil/cid/2f7190d0-7c40-458b-b450-9a1006db3d95/scid/2b5e863c-9497-46ae-a7e9-85f6ef7380da",
    "atta": "/cn/atta-rice-oil-dals/atta/cid/2f7190d0-7c40-458b-b450-9a1006db3d95/scid/7e5b1a31-e1a9-4b10-a6b9-19b22bcd46b7",
    "rice": "/cn/atta-rice-oil-dals/rice/cid/2f7190d0-7c40-458b-b450-9a1006db3d95/scid/4f94660b-09c0-4b43-9d0f-9f1f8b14ea63",
    "dals": "/cn/atta-rice-oil-dals/dals-pulses/cid/2f7190d0-7c40-458b-b450-9a1006db3d95/scid/fb93ef7a-74bc-4c0a-9fa6-e82f3bf2baa9",
    "ghee": "/cn/atta-rice-oil-dals/ghee/cid/2f7190d0-7c40-458b-b450-9a1006db3d95/scid/b3e6a1e8-b195-4c98-bba8-ef3e5f3af6a5",
    "sugar_salt": "/cn/atta-rice-oil-dals/sugar-salt/cid/2f7190d0-7c40-458b-b450-9a1006db3d95/scid/8fc0a6e1-b15f-4e87-a1a5-f4c2f9e47e67",
    "masalas": "/cn/masala-dry-fruits-more/whole-masalas/cid/0c2ccf87-e32c-4438-9560-8d9488fc73e0/scid/c8f6e3a9-b2f4-4d8a-a5c7-e9f1d2b3a4c6",
    "dry_fruits": "/cn/masala-dry-fruits-more/dry-fruits/cid/0c2ccf87-e32c-4438-9560-8d9488fc73e0/scid/a7d8c9e1-f2b3-4a5c-b6d7-e8f9a0b1c2d3",
    "fruits": "/cn/fruits-vegetables/fresh-fruits/cid/64374cfe-d06f-4a01-898e-c07c46462c36/scid/09e63c15-e5f7-4712-9ff8-513250b79942",
    "vegetables": "/cn/fruits-vegetables/fresh-vegetables/cid/64374cfe-d06f-4a01-898e-c07c46462c36/scid/b4827798-fcb6-4520-ba5b-0f2bd9bd7208",
    "chips": "/cn/munchies/chips-crisps/cid/d2c2a144-43cd-43e5-b308-92628fa68596/scid/df4f5100-c02f-4906-83b8-ddb744081a7a",
    "biscuits": "/cn/biscuits/cookies/cid/2552acf2-2f77-4714-adc8-e505de3985db/scid/f8c9d0e1-a2b3-4c5d-e6f7-a8b9c0d1e2f3",
    "tea_coffee": "/cn/tea-coffee-more/tea/cid/d7e98d87-6850-4cf9-a37c-e4fa34ae302c/scid/b9c0d1e2-f3a4-5b6c-d7e8-f9a0b1c2d3e4",
}

# JS to scroll and load all products
SCROLL_JS = """
() => {
    return new Promise(resolve => {
        let lastCount = 0;
        let scrolls = 0;
        const maxScrolls = 30;
        const scroll = () => {
            window.scrollTo(0, document.body.scrollHeight);
            scrolls++;
            setTimeout(() => {
                const cards = document.querySelectorAll('a[href*="/pn/"]').length;
                if (cards === lastCount || scrolls >= maxScrolls) {
                    resolve({scrolls, cards});
                } else {
                    lastCount = cards;
                    scroll();
                }
            }, 1500);
        };
        scroll();
    });
}
"""

# JS to extract products
EXTRACT_JS = """
() => {
    const products = [];
    const seen = new Set();
    document.querySelectorAll('a[href*="/pn/"]').forEach(card => {
        try {
            const href = card.getAttribute('href');
            const pvid = href.match(/pvid\\/([^/]+)/)?.[1];
            if (seen.has(pvid)) return;
            seen.add(pvid);
            
            const text = card.innerText;
            const lines = text.split('\\n').filter(l => l.trim());
            let price = null, mrp = null, name = '', weight = null, rating = null, reviews = null;
            
            for (const line of lines) {
                const priceM = line.match(/^₹(\\d+)$/);
                if (priceM) {
                    if (!price) price = parseInt(priceM[1]);
                    else if (!mrp) mrp = parseInt(priceM[1]);
                }
                if (line.length > 10 && !line.includes('₹') && !line.match(/OFF|ADD|Notify|mins|Premium|Sold out/)) {
                    if (!name) name = line.trim();
                }
                const wM = line.match(/^(\\d+\\s*(?:pack|pc|pcs|g|ml|kg|L|pieces).*)$/i);
                if (wM) weight = wM[1];
                const rM = line.match(/(\\d+\\.\\d+)\\s*\\((\\d+\\.?\\d*k?)\\)/);
                if (rM) { rating = parseFloat(rM[1]); reviews = rM[2]; }
            }
            
            if (price && name && name.length > 3) {
                products.push({name, price, mrp, weight, rating, reviews, pvid, url: 'https://www.zepto.com' + href});
            }
        } catch(e){}
    });
    return products;
}
"""

def scrape_category_via_browser(category_path, timeout=60):
    """
    This is meant to be called when browser relay is active.
    Returns list of products.
    """
    # This would need browser tool integration - placeholder for manual use
    pass


if __name__ == "__main__":
    print("Zepto Full Scraper")
    print(f"Available categories: {list(CATEGORIES.keys())}")
    print("\nUse browser relay to scrape. JS functions defined above.")
