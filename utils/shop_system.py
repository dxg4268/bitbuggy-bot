import discord
from discord.ext import commands
import sqlite3
from utils.embeds import create_shop_embed, create_purchase_embed
import os
import time
import traceback
from utils.db_monitor import check_db_status

class ShopSystem(commands.Cog):
    def __init__(self, bot, shop_channel_id):
        self.bot = bot
        self.shop_channel_id = shop_channel_id
        self.conn = self.connect_with_retry()
        self.c = self.conn.cursor()
        print(f"ShopSystem: Initialized with shop channel ID: {shop_channel_id}")
        
    def connect_with_retry(self, max_retries=5, retry_delay=1):
        """Connect to the database with retry logic"""
        DB_PATH = os.getenv('DB_PATH', 'shop.db')
        retries = 0
        last_error = None
        
        while retries < max_retries:
            try:
                conn = sqlite3.connect(DB_PATH)
                print(f"ShopSystem: Successfully connected to database at {DB_PATH}")
                return conn
            except sqlite3.Error as e:
                last_error = e
                retries += 1
                print(f"ShopSystem: Database connection error (attempt {retries}/{max_retries}): {e}")
                if retries < max_retries:
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
        
        # If we get here, all retries failed
        raise last_error or sqlite3.Error("ShopSystem: Failed to connect to database after multiple attempts")
        
    def cog_unload(self):
        self.conn.close()
        
    @commands.command()
    async def shop(self, ctx):
        if ctx.channel.id != self.shop_channel_id:
            return await ctx.send("🛍️ The shop is only open in the designated channel!")

        try:
            # Get shop items from database
            self.c.execute("SELECT id, name, price, role_id FROM shop_items")
            shop_items = self.c.fetchall()
            
            if not shop_items:
                return await ctx.send("The shop is currently empty!")
                
            # Create embed
            embed = create_shop_embed()
            
            # Create view with select menu
            view = ShopView(ctx.author, ctx, shop_items)
            await ctx.send(embed=embed, view=view)
        except Exception as e:
            print(f"ShopSystem: Error displaying shop: {e}")
            await ctx.send("❌ There was an error accessing the shop. Please try again later.")

class ShopView(discord.ui.View):
    def __init__(self, user, ctx, shop_items):
        super().__init__()
        self.user = user
        self.ctx = ctx
        self.shop_items = shop_items

        options = [
            discord.SelectOption(label=item[1], description=f"{item[2]} coins", value=str(item[0]))
            for item in shop_items
        ]
        self.select_menu = discord.ui.Select(placeholder="Choose an item to buy...", options=options)
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("This shop isn't for you.", ephemeral=True)
            return

        item_id = int(self.select_menu.values[0])
        selected_item = next(item for item in self.shop_items if item[0] == item_id)
        item_name = selected_item[1]
        item_price = selected_item[2]
        
        view = ConfirmPurchase(selected_item, self.user, self.ctx)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🛒 Confirm Purchase",
                description=f"Are you sure you want to buy **{item_name}** for **{item_price}** coins?",
                color=discord.Color.blue()
            ),
            view=view,
            ephemeral=True
        )

class ConfirmPurchase(discord.ui.View):
    def __init__(self, item, user, ctx):
        super().__init__()
        self.item = item  # (id, name, price, role_id)
        self.user = user
        self.ctx = ctx
        self.conn = self.connect_with_retry()
        self.c = self.conn.cursor()

    def connect_with_retry(self, max_retries=5, initial_delay=1):
        """
        Connect to the database with a retry mechanism in case of connection failures.
        
        Args:
            max_retries: Maximum number of connection attempts
            initial_delay: Initial delay between retries in seconds (will increase exponentially)
            
        Returns:
            sqlite3.Connection object if successful
            
        Raises:
            Exception: If all connection attempts fail
        """
        db_path = os.getenv('DB_PATH', 'shop.db')
        
        retry_count = 0
        delay = initial_delay
        last_exception = None
        
        while retry_count < max_retries:
            try:
                conn = sqlite3.connect(db_path)
                print(f"Purchase: Connected to database at {db_path}")
                return conn
            except sqlite3.Error as e:
                last_exception = e
                retry_count += 1
                if retry_count < max_retries:
                    print(f"Database connection attempt {retry_count} failed. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                
        # If we got here, all retries failed
        print("All database connection attempts failed. Running diagnostics...")
        check_db_status()  # Run diagnostics to help troubleshoot the issue
        raise last_exception

    def __del__(self):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("You can't confirm someone else's purchase.", ephemeral=True)
            return

        item_name = self.item[1]
        item_price = self.item[2]
        role_id = self.item[3]

        try:
            self.c.execute("SELECT balance FROM users WHERE user_id = ?", (self.user.id,))
            result = self.c.fetchone()
            if not result or result[0] < item_price:
                embed = create_purchase_embed(item_name, item_price, success=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            new_balance = result[0] - item_price
            self.c.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, self.user.id))
            self.conn.commit()

            role = self.ctx.guild.get_role(role_id)
            if role:
                await self.user.add_roles(role)
                embed = create_purchase_embed(item_name, item_price, success=True)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("Role not found. Please contact an admin.", ephemeral=True)
        except Exception as e:
            print(f"Purchase: Error processing purchase: {e}")
            traceback.print_exc()
            check_db_status()  # Run diagnostics when purchase fails
            await interaction.response.send_message("There was an error processing your purchase. Please try again later.", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.user:
            await interaction.response.send_message("❌ Purchase cancelled.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ShopSystem(bot, int(bot.shop_channel_id)))
