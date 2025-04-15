import discord
from discord.ext import commands
import sqlite3
import random
import os
import asyncio
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
import traceback

# Try to load environment variables from .env file, but don't fail if it doesn't exist
try:
    load_dotenv(verbose=False)
except:
    pass  # .env file not found, will use environment variables directly

# Create utils directory if it doesn't exist
if not os.path.exists("utils"):
    os.makedirs("utils")

# Get token and channel IDs from environment variables
TOKEN = os.getenv('DISCORD_TOKEN')
SHOP_CHANNEL_ID = int(os.getenv('SHOP_CHANNEL_ID', '0'))
COMMAND_CHANNELS = [int(channel_id.strip()) for channel_id in os.getenv('COMMAND_CHANNELS', '').split(',') if channel_id.strip()]
POINTS_CHANNEL_ID = int(os.getenv('POINTS_CHANNEL_ID', '0'))

# Check if the token is available
if not TOKEN:
    raise ValueError("No Discord token found. Please set the DISCORD_TOKEN environment variable.")

if SHOP_CHANNEL_ID == 0:
    print("Warning: SHOP_CHANNEL_ID not set properly. Please set this environment variable.")

if not COMMAND_CHANNELS:
    print("Warning: COMMAND_CHANNELS not set properly. Please set this environment variable.")

if POINTS_CHANNEL_ID == 0:
    print("Warning: POINTS_CHANNEL_ID not set properly. Please set this environment variable.")

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot.shop_channel_id = SHOP_CHANNEL_ID  # Store as attribute for extensions to use
bot.command_channels = COMMAND_CHANNELS  # Store command channels
bot.points_channel_id = POINTS_CHANNEL_ID  # Store points channel

# Get database path - use environment variable in Docker or default path
DB_PATH = os.getenv('DB_PATH', 'shop.db')
print(f"Using database path: {DB_PATH}")

# Ensure data directory exists if using Docker path
if os.path.dirname(DB_PATH) and not os.path.exists(os.path.dirname(DB_PATH)):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    print(f"Created directory: {os.path.dirname(DB_PATH)}")

# Initialize database with retry logic
def init_database(max_retries=5, retry_delay=2):
    """Initialize the database with retry logic for cloud deployments"""
    retries = 0
    last_error = None
    
    while retries < max_retries:
        try:
            # Set up database
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Create tables
            c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER)''')
            c.execute('''CREATE TABLE IF NOT EXISTS shop_items (
                        id INTEGER PRIMARY KEY,
                        name TEXT,
                        price INTEGER,
                        role_id INTEGER)''')
            c.execute('''CREATE TABLE IF NOT EXISTS admin_roles (role_id INTEGER PRIMARY KEY)''')
            c.execute('''CREATE TABLE IF NOT EXISTS daily_rewards 
                        (user_id INTEGER PRIMARY KEY, 
                        last_claim TIMESTAMP,
                        streak INTEGER DEFAULT 0)''')
            conn.commit()
            
            # Add sample shop items if table is empty
            c.execute("SELECT COUNT(*) FROM shop_items")
            if c.fetchone()[0] == 0:
                sample_items = [
                    ("🪼Furina", 50000, 1361011749913890816),
                    ("🌟Navia", 50000, 1361012791791845477), 
                    ("🌸Raiden Shogun", 50000, 1361013400758386868),
                    ("☠One Piece", 50000, 1361014183927349468),
                    ("🦊Naruto", 50000, 1361014693459656805),
                    ("愛Bleach", 50000, 1361014463943147721),
                    ("💎VIP", 100000, 1361014938155483298)
                ]
                c.executemany("INSERT INTO shop_items (name, price, role_id) VALUES (?, ?, ?)", sample_items)
                conn.commit()
                print("Initialized shop items.")
            
            print("Database initialization successful.")
            return conn
            
        except sqlite3.Error as e:
            last_error = e
            retries += 1
            print(f"Database initialization error (attempt {retries}/{max_retries}): {e}")
            
            # Check if directory is writable
            if os.path.dirname(DB_PATH):
                try:
                    test_file = os.path.join(os.path.dirname(DB_PATH), 'test_write.txt')
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    print(f"Directory {os.path.dirname(DB_PATH)} is writable.")
                except Exception as e:
                    print(f"Directory write test failed: {e}")
            
            if retries < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 1.5  # Exponential backoff
    
    # If we get here, all retries failed
    raise last_error or sqlite3.Error("Failed to initialize database after multiple attempts")

# Initialize database connection
conn = init_database()
c = conn.cursor()

# Define a simple HTTP handler for health checks
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Bot is running')
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        # Suppress log messages to avoid cluttering console
        return

# Start HTTP server for health checks
def start_http_server():
    port = int(os.getenv('PORT', 8000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"Starting health check server on port {port}")
    server.serve_forever()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print(f"Ready to serve {len(bot.guilds)} guilds")
    print(f"Using database: {DB_PATH}")
    print(f"Command channels: {COMMAND_CHANNELS}")
    print(f"Points channel: {POINTS_CHANNEL_ID}")
    print("------")
    
    # Load extensions
    await load_extensions()
    
    print("\nPermission system:")
    print("- Regular users can use: !balance, !shop, !daily")
    print("- Admin users (with specific roles) can use: !admin commands")
    print("- To add admin roles, use: !admin addrole @role")
    print("- To view current admin roles, use: !admin listroles")
    print("------")

async def load_extensions():
    """Load all cog extensions"""
    # Load extensions asynchronously
    for ext in ["utils.admin_tools", "utils.daily_rewards", "utils.shop_system"]:
        try:
            await bot.load_extension(ext)
            print(f"Loaded extension: {ext}")
        except Exception as e:
            print(f"Failed to load extension {ext}: {e}")
            traceback.print_exc()  # Add this line to see full error details

# XP + currency system (basic message earning)
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Only accumulate points in the designated points channel
    if message.channel.id == POINTS_CHANNEL_ID:
        user_id = message.author.id
        c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = c.fetchone()

        if result:
            new_balance = result[0] + random.randint(10, 50)
            c.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        else:
            new_balance = random.randint(10, 50)
            c.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, new_balance))

        conn.commit()

    # Process commands only in allowed channels
    if message.channel.id in COMMAND_CHANNELS:
        await bot.process_commands(message)

# Show user balance with embed
@bot.command()
async def balance(ctx):
    # Debug logging
    print(f"Balance command called in channel {ctx.channel.id}")
    print(f"Command channels: {COMMAND_CHANNELS}")
    
    # Check if command is used in an allowed channel
    if ctx.channel.id not in COMMAND_CHANNELS:
        print(f"Balance command rejected - channel {ctx.channel.id} not in allowed channels")
        return await ctx.send("❌ This command can only be used in designated command channels.")
    
    from utils.embeds import create_balance_embed
    
    user_id = ctx.author.id
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    
    if result:
        embed = create_balance_embed(ctx.author, result[0])
    else:
        embed = create_balance_embed(ctx.author, 0)
        
    await ctx.send(embed=embed)

# Cleanly close the database connection on exit
def cleanup():
    if conn:
        conn.close()
        print("Database connection closed.")

# Start the bot
if __name__ == "__main__":
    # Start HTTP server in a separate thread for health checks
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()
    
    try:
        bot.run(TOKEN)
    finally:
        # Ensure we clean up resources
        cleanup()
