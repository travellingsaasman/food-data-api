#!/usr/bin/env python3
"""
Zepto Batch Category Scraper
Scrapes all food subcategories via browser automation.

This script generates commands for OpenClaw browser relay.
Run it to get the list of URLs to scrape, then use browser automation.
"""

import json
import os
from datetime import datetime

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/data/zepto'

def load_subcategories():
    """Load all food subcategory URLs"""
    with open(f'{DATA_DIR}/food_subcategory_urls.json') as f:
        return json.load(f)

def get_scraped_categories():
    """Get list of already scraped categories from live_prices/"""
    scraped = set()
    prices_dir = f'{DATA_DIR}/live_prices'
    if os.path.exists(prices_dir):
        for f in os.listdir(prices_dir):
            if f.endswith('.json'):
                # Extract category name from filename
                name = f.replace('_2026-02-18.json', '').replace('_', ' ')
                scraped.add(name.lower())
    return scraped

def get_remaining_categories():
    """Get categories that haven't been scraped yet"""
    all_cats = load_subcategories()
    scraped = get_scraped_categories()
    
    remaining = []
    for cat in all_cats:
        cat_key = cat['subcategory'].lower().replace(' ', '_').replace('&', '').replace('-', '_')
        # Check various name formats
        if not any(s in cat['subcategory'].lower() for s in scraped):
            remaining.append(cat)
    
    return remaining

# JavaScript for category page scraping (with infinite scroll)
CATEGORY_SCRAPE_JS = """
() => { 
    return new Promise(resolve => { 
        let lastCount = 0; 
        let stableCount = 0; 
        let scrolls = 0; 
        
        const scroll = () => { 
            window.scrollTo(0, document.body.scrollHeight); 
            scrolls++; 
            
            setTimeout(() => { 
                const cards = document.querySelectorAll('a[href*="/pn/"]').length; 
                
                if (cards === lastCount) { 
                    stableCount++; 
                    if (stableCount >= 6) { 
                        // Extract products
                        const products = []; 
                        const seen = new Set(); 
                        
                        document.querySelectorAll('a[href*="/pn/"]').forEach(card => { 
                            try { 
                                const href = card.getAttribute('href'); 
                                const pvid = href.match(/pvid\\/([^/]+)/)?.[1]; 
                                if (!pvid || seen.has(pvid)) return; 
                                seen.add(pvid); 
                                
                                const text = card.innerText; 
                                const lines = text.split('\\n').filter(l => l.trim()); 
                                let price = null, mrp = null, name = '', weight = null; 
                                
                                for (const line of lines) { 
                                    const priceM = line.match(/^₹(\\d+)$/); 
                                    if (priceM) { 
                                        if (!price) price = parseInt(priceM[1]); 
                                        else if (!mrp) mrp = parseInt(priceM[1]); 
                                    } 
                                    if (line.length > 3 && !line.includes('₹') && !line.match(/OFF|ADD|Notify|mins|Premium|Sold out/i)) { 
                                        if (!name) name = line.trim(); 
                                    } 
                                    const wM = line.match(/^(\\d+\\s*(?:pack|pc|pcs|g|ml|kg|L).*)$/i); 
                                    if (wM) weight = wM[1]; 
                                } 
                                
                                if (price && name && name.length > 2) {
                                    products.push({
                                        name, price, mrp, weight, pvid,
                                        url: 'https://www.zepto.com' + href
                                    });
                                }
                            } catch(e){} 
                        }); 
                        
                        resolve({
                            category: document.querySelector('h1')?.textContent?.replace('Buy ', '').replace(' Online', '') || 'Unknown', 
                            url: window.location.href,
                            scrolls, 
                            count: products.length, 
                            products
                        }); 
                        return; 
                    } 
                } else { 
                    stableCount = 0; 
                    lastCount = cards; 
                } 
                
                if (scrolls >= 80) {
                    resolve({msg: 'max_scrolls', scrolls, cards}); 
                } else {
                    scroll();
                }
            }, 500); 
        }; 
        
        scroll(); 
    }); 
}
"""

if __name__ == '__main__':
    remaining = get_remaining_categories()
    
    print(f"=== Zepto Batch Scraper ===")
    print(f"Total food subcategories: 101")
    print(f"Already scraped: {101 - len(remaining)}")
    print(f"Remaining: {len(remaining)}")
    print()
    
    if remaining:
        print("Next 10 categories to scrape:")
        for i, cat in enumerate(remaining[:10]):
            print(f"  {i+1}. {cat['category']} > {cat['subcategory']}")
            print(f"     {cat['url']}")
        
        print()
        print("URLs for browser automation:")
        for cat in remaining[:10]:
            print(cat['url'])
