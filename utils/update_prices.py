import os
import sqlite3
import sys

def update_shop_prices():
    """Update existing shop item prices to new balanced values"""
    db_path = os.getenv('DB_PATH', 'shop.db')
    
    print(f"\n===== UPDATING SHOP PRICES =====")
    print(f"Database Path: {db_path}")
    
    if not os.path.exists(db_path):
        print("❌ Database file not found!")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get current prices
        cursor.execute("SELECT id, name, price, role_id FROM shop_items")
        items = cursor.fetchall()
        
        if not items:
            print("❌ No shop items found in database!")
            return False
        
        print(f"Found {len(items)} shop items in database.")
        print("\nCURRENT PRICES:")
        for item in items:
            print(f"  - {item[1]}: {item[2]:,} coins")
        
        # Define new prices
        new_prices = {
            "Furina": 50000,
            "Navia": 50000,
            "Raiden Shogun": 50000,
            "One Piece": 50000,
            "Naruto": 50000,
            "Bleach": 50000,
            "VIP": 100000
        }
        
        # Update prices for each item
        updated_count = 0
        for item in items:
            item_id, name, old_price, role_id = item
            clean_name = name.strip("🪼🌟🌸☠🦊愛💎")  # Remove emojis
            
            # Find matching item
            for key in new_prices:
                if key in clean_name:
                    cursor.execute("UPDATE shop_items SET price = ? WHERE id = ?", (new_prices[key], item_id))
                    print(f"✅ Updated {name}: {old_price:,} -> {new_prices[key]:,} coins")
                    updated_count += 1
                    break
        
        conn.commit()
        
        # Verify updates
        cursor.execute("SELECT id, name, price FROM shop_items")
        updated_items = cursor.fetchall()
        
        print(f"\nSUCCESSFULLY UPDATED {updated_count} ITEMS!")
        print("\nNEW PRICES:")
        for item in updated_items:
            print(f"  - {item[1]}: {item[2]:,} coins")
        
        conn.close()
        return True
    
    except Exception as e:
        print(f"❌ Error updating shop prices: {e}")
        return False

if __name__ == "__main__":
    print("Running shop price update script...")
    if update_shop_prices():
        print("\nShop prices have been successfully updated! 🎉")
        print("Note: This won't affect shop items displayed in existing embeds.")
        print("Users will see new prices when they use !shop command.")
        sys.exit(0)
    else:
        print("\nFailed to update shop prices. Check the errors above.")
        sys.exit(1) 