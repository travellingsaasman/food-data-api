#!/usr/bin/env python3
"""
Zepto Product Detail Scraper
Extracts nutrition, ingredients, and detailed product info from product pages.

Usage: This is designed to be called from browser automation.
The JS extraction function can be used directly in browser.act(evaluate).
"""

# JavaScript extraction function for browser.act(evaluate)
EXTRACTION_JS = """
() => {
    const product = {};
    
    // Basic info
    product.name = document.querySelector('h1')?.innerText?.trim();
    product.url = window.location.href;
    
    // Price
    const priceEl = document.body.innerText.match(/₹\\s*(\\d+)\\s*MRP/);
    product.price = priceEl ? parseInt(priceEl[1]) : null;
    const mrpEl = document.body.innerText.match(/MRP\\s*₹\\s*(\\d+)/);
    product.mrp = mrpEl ? parseInt(mrpEl[1]) : null;
    
    // Weight
    const weightMatch = document.body.innerText.match(/Net Qty:\\s*([^•]+)/);
    product.weight = weightMatch ? weightMatch[1].trim() : null;
    
    // Nutrition (standard FSSAI format)
    const text = document.body.innerText;
    const nutritionMatch = text.match(/Energy \\(kcal\\) ([\\d.]+).*?Protein \\(g\\) ([\\d.]+).*?Carbohydrate \\(g\\) ([\\d.]+).*?Total Sugars \\(g\\) ([\\d.]+).*?Added Sugars \\(g\\) ([\\d.]+).*?Dietary Fibre \\(g\\) ([\\d.]+).*?Total Fat \\(g\\) ([\\d.]+).*?Saturated Fat \\(g\\) ([\\d.]+).*?Trans Fat \\(g\\) ([\\d.]+).*?Sodium \\(mg\\) ([\\d.]+)/);
    
    if (nutritionMatch) {
        product.nutrition = {
            energy_kcal: parseFloat(nutritionMatch[1]),
            protein_g: parseFloat(nutritionMatch[2]),
            carbs_g: parseFloat(nutritionMatch[3]),
            sugar_g: parseFloat(nutritionMatch[4]),
            added_sugar_g: parseFloat(nutritionMatch[5]),
            fiber_g: parseFloat(nutritionMatch[6]),
            fat_g: parseFloat(nutritionMatch[7]),
            saturated_fat_g: parseFloat(nutritionMatch[8]),
            trans_fat_g: parseFloat(nutritionMatch[9]),
            sodium_mg: parseFloat(nutritionMatch[10])
        };
    }
    
    // Ingredients
    const ingredientsMatch = text.match(/Ingredients\\s+([^\\n]+)/i);
    product.ingredients = ingredientsMatch ? ingredientsMatch[1].trim() : null;
    
    // FSSAI
    const fssaiMatch = text.match(/License No\\.\\s*([\\d]+)/);
    product.fssai = fssaiMatch ? fssaiMatch[1] : null;
    
    // Brand
    const brandMatch = text.match(/Brand\\s+([A-Za-z][A-Za-z\\s]+?)\\s+Product Type/);
    product.brand = brandMatch ? brandMatch[1].trim() : null;
    
    // Manufacturer
    const mfgMatch = text.match(/Manufacturer Name\\s+([^\\n]+)/);
    product.manufacturer = mfgMatch ? mfgMatch[1].trim() : null;
    
    // Dietary preference
    product.is_veg = text.includes('Dietary Preference') && text.includes('Veg');
    
    // Shelf life
    const shelfMatch = text.match(/Shelf Life\\s+([^\\n]+)/);
    product.shelf_life = shelfMatch ? shelfMatch[1].trim() : null;
    
    return product;
}
"""

# Computed nutrition metrics
def compute_nutrition_metrics(product: dict) -> dict:
    """Add computed nutrition metrics for analysis"""
    
    if not product.get('nutrition') or not product.get('price'):
        return product
    
    nutrition = product['nutrition']
    price = product['price']
    
    # Parse weight to grams
    weight_str = product.get('weight', '')
    weight_g = None
    if 'kg' in weight_str.lower():
        match = re.search(r'([\d.]+)\s*kg', weight_str.lower())
        if match:
            weight_g = float(match.group(1)) * 1000
    elif 'g' in weight_str.lower():
        match = re.search(r'([\d.]+)\s*g', weight_str.lower())
        if match:
            weight_g = float(match.group(1))
    
    if weight_g and weight_g > 0:
        # Per 100g values (nutrition is usually per 100g)
        # Price efficiency metrics
        product['metrics'] = {
            'price_per_100g': round(price / weight_g * 100, 2),
            'price_per_10g_protein': round(price / (nutrition['protein_g'] * weight_g / 100) * 10, 2) if nutrition['protein_g'] > 0 else None,
            'price_per_1000kcal': round(price / (nutrition['energy_kcal'] * weight_g / 100) * 1000, 2) if nutrition['energy_kcal'] > 0 else None,
            'protein_density': round(nutrition['protein_g'] / nutrition['energy_kcal'] * 100, 2) if nutrition['energy_kcal'] > 0 else None,
            'sugar_to_fiber_ratio': round(nutrition['sugar_g'] / nutrition['fiber_g'], 2) if nutrition['fiber_g'] > 0 else None,
        }
    
    return product


# Ingredient red flags
RED_FLAG_INGREDIENTS = [
    ('palm oil', 'unhealthy_fat'),
    ('palmolein', 'unhealthy_fat'),
    ('hydrogenated', 'trans_fat_risk'),
    ('maltodextrin', 'hidden_sugar'),
    ('high fructose', 'hidden_sugar'),
    ('aspartame', 'artificial_sweetener'),
    ('sucralose', 'artificial_sweetener'),
    ('msg', 'flavor_enhancer'),
    ('monosodium glutamate', 'flavor_enhancer'),
    ('yeast extract', 'hidden_msg'),
    ('hydrolyzed', 'hidden_msg'),
    ('artificial color', 'artificial_additive'),
    ('colour', 'artificial_additive'),  # Check for numbered colors like 160C
    ('tbhq', 'preservative'),
    ('bht', 'preservative'),
    ('sodium benzoate', 'preservative'),
]

def flag_ingredients(ingredients: str) -> list:
    """Return list of red flags found in ingredients"""
    if not ingredients:
        return []
    
    ingredients_lower = ingredients.lower()
    flags = []
    
    for pattern, flag_type in RED_FLAG_INGREDIENTS:
        if pattern in ingredients_lower:
            flags.append({'ingredient': pattern, 'flag': flag_type})
    
    return flags


if __name__ == '__main__':
    import re
    
    # Example usage
    sample = {
        'name': "Lay's Magic Masala",
        'price': 18,
        'weight': '1 pack (48 g)',
        'ingredients': 'Potato, Edible Vegetable Oil (Palmolein, Rice Bran Oil), Seasoning (Maltodextrin, Color (160C))',
        'nutrition': {
            'energy_kcal': 536,
            'protein_g': 6.0,
            'carbs_g': 52,
            'sugar_g': 2,
            'fiber_g': 4,
            'fat_g': 33
        }
    }
    
    print("Red flags:", flag_ingredients(sample['ingredients']))
    print("\nExtraction JS saved. Use EXTRACTION_JS in browser.act(evaluate)")
