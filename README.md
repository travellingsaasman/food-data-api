# Indian Food Data API

**Product catalog and price tracking for Indian grocery platforms.**

Built by scraping Zepto's sitemap and parsing saved HTML pages for live prices.

## Quick Start

```bash
# API is running on port 8002
curl http://localhost:8002/stats

# Search products
curl "http://localhost:8002/products?q=paneer"

# Get prices
curl "http://localhost:8002/prices?q=peanut"
```

## API Endpoints

### Product Catalog (from sitemap)

| Endpoint | Description |
|----------|-------------|
| `GET /stats` | Catalog statistics |
| `GET /products?q=&brand=&category=&limit=&offset=` | Search/list products |
| `GET /products/{id}` | Get product by ID |
| `GET /brands?q=` | Search brands |
| `GET /brands/{id}` | Get brand with sample products |
| `GET /categories` | List all categories |
| `GET /search/advanced?name=&weight_min=&weight_max=` | Advanced search |

### Price Tracking (from HTML pages)

| Endpoint | Description |
|----------|-------------|
| `POST /prices/ingest` | Ingest price data from parsed HTML |
| `GET /prices?q=&source=` | Get tracked prices |
| `GET /prices/{key}` | Get price history for product |

## Data Sources

### Sitemap Scraper
- Fetches all products from Zepto's XML sitemaps
- ~220K products → filtered to ~55K food products
- Run: `python scrapers/zepto_sitemap_scraper.py`

### HTML Parser (for prices)
- Parses saved HTML pages from Zepto (view-source format)
- Extracts: name, packsize, MRP, selling price, discount %
- Run: `python scrapers/zepto_html_parser.py <file.html> [output.json]`

## Workflow for Price Capture

Since Zepto blocks automated scraping, use manual HTML capture:

1. Open Zepto in Chrome, navigate to category page
2. Right-click → "View Page Source"
3. Save the page (Ctrl+S) as HTML
4. Parse with: `python scrapers/zepto_html_parser.py saved_page.html prices.json`
5. Ingest: `curl -X POST http://localhost:8002/prices/ingest -d @prices.json`

## Stats

| Metric | Count |
|--------|-------|
| Total Products | 54,811 |
| Brands | 2,767 |
| Categories | 338 |
| Products with Weight | 8,732 |

## Deployment

```bash
# Run with PM2
pm2 start ecosystem.config.js

# Or directly
cd api && uvicorn main:app --host 0.0.0.0 --port 8002
```

## License

MIT
