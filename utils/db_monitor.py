import os
import sqlite3
import datetime
import sys

def check_db_status():
    """
    Utility function to check database status and perform basic diagnostics.
    Can be run manually via the command line or imported and used in the bot.
    """
    db_path = os.getenv('DB_PATH', 'shop.db')
    data_dir = os.path.dirname(db_path) if '/' in db_path else '.'
    
    print(f"\n===== DATABASE STATUS CHECK =====")
    print(f"Timestamp: {datetime.datetime.now().isoformat()}")
    print(f"Database Path: {db_path}")
    print(f"Data Directory: {data_dir}")
    
    # Check if data directory exists and is writable
    if os.path.exists(data_dir):
        print(f"✅ Data directory exists")
        if os.access(data_dir, os.W_OK):
            print(f"✅ Data directory is writable")
        else:
            print(f"❌ Data directory is NOT writable!")
            print(f"   Directory permissions: {oct(os.stat(data_dir).st_mode & 0o777)}")
            print(f"   Directory owner: {os.stat(data_dir).st_uid}")
    else:
        print(f"❌ Data directory does NOT exist!")
        try:
            os.makedirs(data_dir, exist_ok=True)
            print(f"✅ Created data directory")
        except Exception as e:
            print(f"❌ Failed to create data directory: {e}")
    
    # Check if database file exists
    if os.path.exists(db_path):
        print(f"✅ Database file exists")
        print(f"   Size: {os.path.getsize(db_path)} bytes")
        print(f"   Last modified: {datetime.datetime.fromtimestamp(os.path.getmtime(db_path)).isoformat()}")
    else:
        print(f"❌ Database file does NOT exist!")
    
    # Try connecting to database
    try:
        conn = sqlite3.connect(db_path)
        print(f"✅ Successfully connected to database")
        
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        if tables:
            print(f"✅ Database has {len(tables)} tables:")
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                print(f"   - {table[0]}: {count} rows")
        else:
            print(f"❌ Database has no tables!")
        
        conn.close()
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
    
    print("================================\n")
    
def reset_database():
    """Reset the database by deleting it and recreating tables"""
    db_path = os.getenv('DB_PATH', 'shop.db')
    
    print(f"\n===== DATABASE RESET =====")
    
    # Delete the database file if it exists
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"✅ Deleted existing database: {db_path}")
        except Exception as e:
            print(f"❌ Failed to delete database: {e}")
            return False
    
    # Create a new database with tables
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            last_activity TEXT
        )
        ''')
        
        # Create shop_items table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS shop_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            role_id INTEGER NOT NULL
        )
        ''')
        
        # Create admin_roles table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_roles (
            role_id INTEGER PRIMARY KEY
        )
        ''')
        
        conn.commit()
        print(f"✅ Created new database with tables")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Failed to create new database: {e}")
        return False

if __name__ == "__main__":
    # When run directly, perform database status check
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        if reset_database():
            print("Database has been reset successfully!")
        else:
            print("Failed to reset database.")
        
        # Also perform a status check after reset
        check_db_status()
    else:
        check_db_status() 