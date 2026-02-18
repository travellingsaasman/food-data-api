#!/usr/bin/env python3
"""
Filter Zepto products to food-only categories
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "zepto"

# Food-related keywords for product filtering
FOOD_KEYWORDS = [
    # Grains & Staples
    'atta', 'flour', 'rice', 'wheat', 'dal', 'pulse', 'lentil', 'chana', 'moong', 
    'toor', 'urad', 'masoor', 'rajma', 'chole', 'besan', 'sooji', 'maida', 'poha',
    'oats', 'muesli', 'cereal', 'cornflakes', 'millet', 'ragi', 'jowar', 'bajra',
    
    # Oils & Ghee
    'oil', 'ghee', 'butter', 'margarine', 'vanaspati',
    
    # Dairy
    'milk', 'curd', 'yogurt', 'yoghurt', 'paneer', 'cheese', 'cream', 'lassi',
    'buttermilk', 'chaach', 'khoa', 'mawa', 'shrikhand',
    
    # Bread & Bakery
    'bread', 'pav', 'bun', 'cake', 'pastry', 'cookie', 'biscuit', 'rusk', 'khari',
    'toast', 'croissant', 'muffin', 'donut', 'brownie',
    
    # Fruits & Vegetables
    'fruit', 'vegetable', 'sabji', 'sabzi', 'apple', 'banana', 'orange', 'mango',
    'grape', 'pomegranate', 'papaya', 'guava', 'watermelon', 'pineapple', 'kiwi',
    'tomato', 'potato', 'onion', 'carrot', 'cabbage', 'cauliflower', 'spinach',
    'palak', 'methi', 'bhindi', 'brinjal', 'capsicum', 'cucumber', 'beans',
    'peas', 'corn', 'mushroom', 'ginger', 'garlic', 'lemon', 'coconut',
    
    # Meat, Fish & Eggs
    'chicken', 'mutton', 'lamb', 'fish', 'prawns', 'shrimp', 'egg', 'meat',
    'sausage', 'salami', 'bacon', 'ham', 'kebab', 'tikka', 'seekh',
    
    # Spices & Masala
    'masala', 'spice', 'turmeric', 'haldi', 'chilli', 'mirch', 'pepper', 
    'cumin', 'jeera', 'coriander', 'dhania', 'cardamom', 'elaichi', 'clove',
    'cinnamon', 'dalchini', 'garam masala', 'biryani masala', 'curry',
    
    # Dry Fruits & Nuts
    'almond', 'badam', 'cashew', 'kaju', 'walnut', 'akhrot', 'pistachio', 'pista',
    'raisin', 'kishmish', 'dates', 'khajoor', 'fig', 'anjeer', 'peanut', 'groundnut',
    
    # Snacks
    'chips', 'namkeen', 'bhujia', 'mixture', 'chakli', 'murukku', 'mathri',
    'papad', 'fryums', 'kurkure', 'nachos', 'popcorn', 'makhana',
    
    # Sweets & Chocolates
    'chocolate', 'candy', 'toffee', 'mithai', 'sweet', 'ladoo', 'barfi', 'halwa',
    'jalebi', 'gulab jamun', 'rasgulla', 'sandesh', 'peda',
    
    # Beverages
    'tea', 'chai', 'coffee', 'juice', 'drink', 'soda', 'cola', 'lemonade',
    'squash', 'sharbat', 'coconut water', 'energy drink', 'health drink',
    
    # Instant & Packaged Food
    'noodles', 'pasta', 'maggi', 'macaroni', 'soup', 'sauce', 'ketchup',
    'mayonnaise', 'pickle', 'achar', 'chutney', 'jam', 'honey', 'spread',
    'ready to eat', 'ready to cook', 'instant', 'frozen', 'paratha', 'roti',
    'samosa', 'spring roll', 'momos', 'pizza', 'burger',
    
    # Condiments
    'salt', 'sugar', 'jaggery', 'gur', 'vinegar', 'soy sauce', 'mustard',
    
    # Baby Food
    'baby food', 'cerelac', 'formula',
    
    # Health Foods
    'protein', 'whey', 'supplement', 'nutrition', 'diet', 'organic', 'gluten free',
    
    # Ice Cream & Frozen Desserts
    'ice cream', 'kulfi', 'frozen dessert', 'gelato', 'sorbet',
]

# Non-food keywords to exclude
EXCLUDE_KEYWORDS = [
    'shirt', 'pant', 'jeans', 'dress', 'saree', 'kurti', 'top', 'bottom',
    'shoe', 'sandal', 'slipper', 'footwear', 'sneaker',
    'phone', 'mobile', 'laptop', 'tablet', 'charger', 'cable', 'earphone',
    'headphone', 'speaker', 'camera', 'watch', 'smartwatch',
    'poster', 'frame', 'decor', 'curtain', 'bedsheet', 'pillow', 'mattress',
    'toy', 'game', 'puzzle', 'doll', 'car', 'bike',
    'cosmetic', 'makeup', 'lipstick', 'foundation', 'mascara', 'eyeliner',
    'shampoo', 'conditioner', 'soap', 'body wash', 'face wash', 'cream',
    'lotion', 'serum', 'sunscreen', 'deodorant', 'perfume', 'fragrance',
    'diaper', 'wipes', 'sanitary', 'pad', 'tampon',
    'detergent', 'cleaner', 'dishwash', 'mop', 'broom', 'bucket',
    'medicine', 'tablet', 'capsule', 'syrup', 'ointment', 'bandage',
    'legging', 'shorts', 'trackpants', 'hoodie', 'sweatshirt', 'jacket',
    't-shirt', 'tshirt', 'polo', 'innerwear', 'underwear', 'bra', 'brief',
    'jewellery', 'jewelry', 'necklace', 'earring', 'bracelet', 'ring',
    'bag', 'backpack', 'handbag', 'wallet', 'purse', 'luggage',
    'book', 'notebook', 'pen', 'pencil', 'stationery', 'office',
    'iphone', 'samsung', 'case', 'cover', 'protector', 'tempered',
]

def is_food_product(product: dict) -> bool:
    """Check if a product is food-related"""
    name = product.get('name', '').lower()
    slug = product.get('slug', '').lower()
    text = f"{name} {slug}"
    
    # First check exclusions
    for kw in EXCLUDE_KEYWORDS:
        if kw in text:
            return False
    
    # Then check inclusions
    for kw in FOOD_KEYWORDS:
        if kw in text:
            return True
    
    return False

def main():
    # Load products
    print("Loading products...")
    with open(DATA_DIR / "products.json") as f:
        data = json.load(f)
    
    products = data['products']
    print(f"Total products: {len(products)}")
    
    # Filter to food only
    print("Filtering to food products...")
    food_products = [p for p in products if is_food_product(p)]
    print(f"Food products: {len(food_products)}")
    
    # Save filtered products
    output = {
        "count": len(food_products),
        "source": "zepto.com",
        "scraped_at": data['scraped_at'],
        "filter": "food_only",
        "products": food_products
    }
    
    output_path = DATA_DIR / "products_food.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"Saved to {output_path}")
    
    # Stats by detected weight
    with_weight = [p for p in food_products if p.get('weight')]
    print(f"Products with detected weight: {len(with_weight)}")
    
    # Sample
    print("\nSample food products:")
    for p in food_products[:10]:
        print(f"  - {p['name'][:60]}... ({p.get('weight', 'N/A')})")

if __name__ == "__main__":
    main()
