#!/usr/bin/env python3
"""
Zepto Price Scraper using Playwright with stealth
Requires: pip install playwright playwright-stealth
Setup: playwright install chromium
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# Koramangala 4th Block, Bengaluru coordinates
LOCATION = {
    "lat": 12.9352,
    "lng": 77.6245,
    "address": "Koramangala 4th Block, Bengaluru"
}

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "zepto" / "prices"

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ]
        )
        
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            geolocation={"latitude": LOCATION["lat"], "longitude": LOCATION["lng"]},
            permissions=["geolocation"],
        )
        
        page = context.new_page()
        
        # Apply stealth
        Stealth().apply_stealth_sync(page)
        
        # Collect API responses
        api_responses = []
        
        def handle_response(response):
            if 'api' in response.url.lower() or 'bff' in response.url.lower():
                try:
                    if response.status == 200:
                        body = response.text()
                        if 'price' in body.lower() or 'mrp' in body.lower():
                            api_responses.append({
                                "url": response.url,
                                "body_preview": body[:500]
                            })
                except:
                    pass
        
        page.on("response", handle_response)
        
        print(f"Navigating to Zepto...")
        
        try:
            # Go to category page
            page.goto(
                "https://www.zepto.com/cn/atta-rice-oil-dals/atta/cid/2f7190d0-7c40-458b-b450-9a1006db3d95/scid/15644eea-d781-4cdd-8d85-e63bd9706b96",
                wait_until="networkidle",
                timeout=60000
            )
            
            page.wait_for_timeout(5000)
            
            # Check if we hit rate limit
            content = page.content()
            if "429" in content or "blocked" in content.lower():
                print("Rate limited!")
                page.screenshot(path=str(OUTPUT_DIR / "rate_limited.png"))
                return
            
            # Take screenshot
            page.screenshot(path=str(OUTPUT_DIR / "page.png"))
            
            # Try to find product cards with prices
            products = page.evaluate(r"""
            () => {
                const products = [];
                // Look for product cards - multiple selector strategies
                const cards = document.querySelectorAll(
                    '[data-testid*="product"], [class*="ProductCard"], [class*="product-card"], ' +
                    '[class*="plp-product"], article'
                );
                
                cards.forEach(card => {
                    const name = card.querySelector('[class*="name"], [class*="title"], [class*="Name"], h3, h4, p')?.textContent?.trim();
                    const priceEl = card.querySelector('[class*="price"], [class*="Price"], [class*="rupee"]');
                    const priceText = priceEl?.textContent || '';
                    const priceMatch = priceText.match(/₹?\s*(\d+(?:\.\d+)?)/);
                    const price = priceMatch ? parseFloat(priceMatch[1]) : null;
                    const img = card.querySelector('img')?.src;
                    const link = card.querySelector('a')?.href;
                    
                    if (name && (price || img)) {
                        products.push({ 
                            name: name.substring(0, 100), 
                            price, 
                            image: img,
                            link 
                        });
                    }
                });
                
                // Also try to find prices in any visible text
                if (products.length === 0) {
                    const allText = document.body.innerText;
                    const priceMatches = allText.match(/₹\s*\d+/g) || [];
                    products.push({
                        note: "No structured products found",
                        price_strings_found: priceMatches.slice(0, 20)
                    });
                }
                
                return products;
            }
            """)
            
            print(f"Found {len(products)} items")
            
            # Save results
            results = {
                "location": LOCATION,
                "scraped_at": datetime.now().isoformat(),
                "products": products,
                "api_responses": api_responses[:20]
            }
            
            output_file = OUTPUT_DIR / f"prices_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)
            
            print(f"Saved to {output_file}")
            print(f"API responses captured: {len(api_responses)}")
            
        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path=str(OUTPUT_DIR / "error.png"))
        
        finally:
            browser.close()

if __name__ == "__main__":
    main()
