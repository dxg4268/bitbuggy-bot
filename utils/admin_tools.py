import discord
from discord.ext import commands
import sqlite3
import datetime
import os
import time

class AdminTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = self.connect_with_retry()
        self.c = self.conn.cursor()
        
        # Create admin_roles table if it doesn't exist
        self.c.execute('''CREATE TABLE IF NOT EXISTS admin_roles 
                       (role_id INTEGER PRIMARY KEY)''')
        self.conn.commit()
        
        # Load admin roles from database
        self.admin_role_ids = self.load_admin_roles()
        
    def connect_with_retry(self, max_retries=5, retry_delay=1):
        """Connect to the database with retry logic"""
        DB_PATH = os.getenv('DB_PATH', 'shop.db')
        retries = 0
        last_error = None
        
        while retries < max_retries:
            try:
                conn = sqlite3.connect(DB_PATH)
                print(f"AdminTools: Successfully connected to database at {DB_PATH}")
                return conn
            except sqlite3.Error as e:
                last_error = e
                retries += 1
                print(f"AdminTools: Database connection error (attempt {retries}/{max_retries}): {e}")
                if retries < max_retries:
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
        
        # If we get here, all retries failed
        raise last_error or sqlite3.Error("AdminTools: Failed to connect to database after multiple attempts")
        
    def load_admin_roles(self):
        """Load admin roles from database"""
        try:
            self.c.execute("SELECT role_id FROM admin_roles")
            return [role_id[0] for role_id in self.c.fetchall()]
        except sqlite3.Error as e:
            print(f"AdminTools: Error loading admin roles: {e}")
            return []
        
    def save_admin_role(self, role_id):
        """Save a role ID to the database"""
        try:
            self.c.execute("INSERT OR IGNORE INTO admin_roles (role_id) VALUES (?)", (role_id,))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"AdminTools: Error saving admin role: {e}")
        
    def remove_admin_role(self, role_id):
        """Remove a role ID from the database"""
        try:
            self.c.execute("DELETE FROM admin_roles WHERE role_id = ?", (role_id,))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"AdminTools: Error removing admin role: {e}")
        
    def cog_unload(self):
        self.conn.close()
        
    async def cog_check(self, ctx):
        """Only allow users with specific roles to use these commands"""
        # Always allow server administrators
        if ctx.author.guild_permissions.administrator:
            return True
            
        # Check if the user has any of the allowed roles
        for role in ctx.author.roles:
            if role.id in self.admin_role_ids:
                return True
                
        # If we get here, the user doesn't have permission
        await ctx.send(embed=discord.Embed(
            title="❌ Permission Denied",
            description="You don't have permission to use admin commands.",
            color=discord.Color.red()
        ))
        return False
        
    @commands.group(name="admin")
    async def admin(self, ctx):
        """Admin commands group"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="Admin Commands",
                description="Here are the available admin commands:",
                color=discord.Color.blue()
            )
            embed.add_field(name="Economy Management", value=(
                "`!admin addcoins @user amount` - Add coins to a user\n"
                "`!admin removecoins @user amount` - Remove coins from a user\n"
                "`!admin viewbalance @user` - View another user's balance"
            ), inline=False)
            embed.add_field(name="Shop Management", value=(
                "`!admin additem name price role_id` - Add an item to the shop\n"
                "`!admin removeitem name` - Remove an item from the shop\n"
                "`!admin updateprice name price` - Update an item's price\n"
                "`!admin listitems` - List all shop items"
            ), inline=False)
            embed.add_field(name="Role Management", value=(
                "`!admin addrole @role` - Add a role that can use admin commands\n"
                "`!admin removerole @role` - Remove a role from admin access\n"
                "`!admin listroles` - List all roles that can use admin commands"
            ), inline=False)
            embed.add_field(name="Daily Rewards", value=(
                "`!admin resetdaily @user` - Reset a user's daily reward"
            ), inline=False)
            embed.add_field(name="Database Management", value=(
                "`!admin updateprices` - Update all shop prices to new values"
            ), inline=False)
            await ctx.send(embed=embed)
        
    # Command to add a role to admin roles list
    @admin.command(name="addrole")
    @commands.has_permissions(administrator=True)  # Only server admins can add admin roles
    async def add_admin_role(self, ctx, role: discord.Role):
        """Add a role to the list of admin roles"""
        if role.id in self.admin_role_ids:
            embed = discord.Embed(
                title="❌ Error",
                description=f"{role.mention} is already an admin role",
                color=discord.Color.red()
            )
        else:
            self.admin_role_ids.append(role.id)
            self.save_admin_role(role.id)
            embed = discord.Embed(
                title="✅ Role Added",
                description=f"{role.mention} can now use admin commands",
                color=discord.Color.green()
            )
            
        await ctx.send(embed=embed)
        
    # Command to remove a role from admin roles list
    @admin.command(name="removerole")
    @commands.has_permissions(administrator=True)  # Only server admins can remove admin roles
    async def remove_admin_role_cmd(self, ctx, role: discord.Role):
        """Remove a role from the list of admin roles"""
        if role.id in self.admin_role_ids:
            self.admin_role_ids.remove(role.id)
            self.remove_admin_role(role.id)
            embed = discord.Embed(
                title="✅ Role Removed",
                description=f"{role.mention} can no longer use admin commands",
                color=discord.Color.orange()
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description=f"{role.mention} is not an admin role",
                color=discord.Color.red()
            )
            
        await ctx.send(embed=embed)
        
    # Command to list admin roles
    @admin.command(name="listroles")
    async def list_admin_roles(self, ctx):
        """List all roles that can use admin commands"""
        embed = discord.Embed(
            title="👑 Admin Roles",
            description="These roles can use admin commands:",
            color=discord.Color.gold()
        )
        
        roles_found = False
        for role_id in self.admin_role_ids:
            role = ctx.guild.get_role(role_id)
            if role:
                embed.add_field(name=role.name, value=f"ID: {role.id}", inline=False)
                roles_found = True
                
        if not roles_found:
            embed.description = "No specific roles have been added. Only server administrators can use admin commands."
            
        embed.set_footer(text="Server administrators can always use admin commands")
        embed.timestamp = datetime.datetime.now()
        
        await ctx.send(embed=embed)
        
    @admin.command(name="addcoins")
    async def add_coins(self, ctx, user: discord.Member, amount: int):
        """Add coins to a user's balance"""
        if amount <= 0:
            embed = discord.Embed(
                title="❌ Error",
                description="Amount must be positive",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
            
        self.c.execute("SELECT balance FROM users WHERE user_id = ?", (user.id,))
        result = self.c.fetchone()
        
        if result:
            new_balance = result[0] + amount
            self.c.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user.id))
        else:
            new_balance = amount
            self.c.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user.id, amount))
            
        self.conn.commit()
        
        embed = discord.Embed(
            title="💰 Coins Added",
            description=f"Added **{amount}** coins to {user.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="New Balance", value=f"**{new_balance}** coins")
        embed.set_footer(text=f"Admin: {ctx.author.name}")
        embed.timestamp = datetime.datetime.now()
        
        await ctx.send(embed=embed)
        
    @admin.command(name="removecoins")
    async def remove_coins(self, ctx, user: discord.Member, amount: int):
        """Remove coins from a user's balance"""
        if amount <= 0:
            embed = discord.Embed(
                title="❌ Error",
                description="Amount must be positive",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
            
        self.c.execute("SELECT balance FROM users WHERE user_id = ?", (user.id,))
        result = self.c.fetchone()
        
        if not result:
            embed = discord.Embed(
                title="❌ Error",
                description=f"{user.mention} doesn't have any coins",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
            
        new_balance = max(0, result[0] - amount)
        self.c.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user.id))
        self.conn.commit()
        
        embed = discord.Embed(
            title="💰 Coins Removed",
            description=f"Removed **{amount}** coins from {user.mention}",
            color=discord.Color.orange()
        )
        embed.add_field(name="New Balance", value=f"**{new_balance}** coins")
        embed.set_footer(text=f"Admin: {ctx.author.name}")
        embed.timestamp = datetime.datetime.now()
        
        await ctx.send(embed=embed)
        
    @admin.command(name="setcoins")
    async def set_coins(self, ctx, user: discord.Member, amount: int):
        """Set a user's coin balance"""
        if amount < 0:
            embed = discord.Embed(
                title="❌ Error",
                description="Amount cannot be negative",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
            
        self.c.execute("SELECT balance FROM users WHERE user_id = ?", (user.id,))
        result = self.c.fetchone()
        
        if result:
            self.c.execute("UPDATE users SET balance = ? WHERE user_id = ?", (amount, user.id))
        else:
            self.c.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user.id, amount))
            
        self.conn.commit()
        
        embed = discord.Embed(
            title="💰 Balance Set",
            description=f"Set {user.mention}'s balance to **{amount}** coins",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Admin: {ctx.author.name}")
        embed.timestamp = datetime.datetime.now()
        
        await ctx.send(embed=embed)
        
    @admin.command(name="viewbalance")
    async def view_balance(self, ctx, user: discord.Member):
        """View a user's coin balance"""
        self.c.execute("SELECT balance FROM users WHERE user_id = ?", (user.id,))
        result = self.c.fetchone()
        
        if result:
            balance = result[0]
        else:
            balance = 0
            
        embed = discord.Embed(
            title="💰 User Balance",
            description=f"{user.mention} has **{balance}** coins",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"Requested by admin: {ctx.author.name}")
        embed.timestamp = datetime.datetime.now()
        
        await ctx.send(embed=embed)
        
    @admin.command(name="resetdaily")
    async def reset_daily(self, ctx, user: discord.Member):
        """Reset a user's daily reward streak and timestamp"""
        self.c.execute("DELETE FROM daily_rewards WHERE user_id = ?", (user.id,))
        self.conn.commit()
        
        embed = discord.Embed(
            title="🔄 Daily Reset",
            description=f"Reset daily rewards for {user.mention}",
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Admin: {ctx.author.name}")
        embed.timestamp = datetime.datetime.now()
        
        await ctx.send(embed=embed)
        
    @admin.command(name="additem")
    async def add_item(self, ctx, name: str, price: int, role_id: int):
        """Add an item to the shop"""
        # Actually connect to the shop database
        self.c.execute("INSERT INTO shop_items (name, price, role_id) VALUES (?, ?, ?)", 
                      (name, price, role_id))
        self.conn.commit()
        
        embed = discord.Embed(
            title="🛒 Item Added",
            description=f"Added **{name}** to the shop for **{price}** coins",
            color=discord.Color.green()
        )
        embed.add_field(name="Role ID", value=str(role_id))
        embed.set_footer(text=f"Admin: {ctx.author.name}")
        embed.timestamp = datetime.datetime.now()
        
        await ctx.send(embed=embed)
        
    @admin.command(name="removeitem")
    async def remove_item(self, ctx, name: str):
        """Remove an item from the shop"""
        # Actually connect to the shop database
        self.c.execute("DELETE FROM shop_items WHERE name = ?", (name,))
        rows_affected = self.c.rowcount
        self.conn.commit()
        
        if rows_affected > 0:
            embed = discord.Embed(
                title="🗑️ Item Removed",
                description=f"Removed **{name}** from the shop",
                color=discord.Color.red()
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Item **{name}** not found in the shop",
                color=discord.Color.red()
            )
            
        embed.set_footer(text=f"Admin: {ctx.author.name}")
        embed.timestamp = datetime.datetime.now()
        
        await ctx.send(embed=embed)
        
    @admin.command(name="updateprice")
    async def update_price(self, ctx, *, args):
        """Update the price of a shop item"""
        try:
            # Extract item name and price from args
            last_space = args.rfind(' ')
            if last_space == -1:
                return await ctx.send("❌ Invalid syntax. Use `!admin updateprice item_name new_price`")
                
            item_name = args[:last_space].strip()
            try:
                new_price = int(args[last_space:].strip())
            except ValueError:
                return await ctx.send("❌ Price must be a number.")
                
            # Find the item by name
            self.c.execute("SELECT id, name, price FROM shop_items WHERE name LIKE ?", (f"%{item_name}%",))
            items = self.c.fetchall()
            
            if not items:
                return await ctx.send(f"❌ No items found matching '{item_name}'.")
                
            if len(items) > 1:
                # Multiple matches, list them
                item_list = "\n".join([f"• {item[1]} ({item[2]:,} coins)" for item in items])
                return await ctx.send(f"Multiple items found. Please be more specific:\n{item_list}")
                
            # Update the price
            item_id, full_name, old_price = items[0]
            self.c.execute("UPDATE shop_items SET price = ? WHERE id = ?", (new_price, item_id))
            self.conn.commit()
            
            embed = discord.Embed(
                title="✅ Price Updated",
                description=f"Updated price for **{full_name}**",
                color=discord.Color.green()
            )
            embed.add_field(name="Old Price", value=f"{old_price:,} coins", inline=True)
            embed.add_field(name="New Price", value=f"{new_price:,} coins", inline=True)
            await ctx.send(embed=embed)
                
        except Exception as e:
            await ctx.send(f"❌ Error updating price: {e}")
            
    @admin.command(name="listitems")
    async def list_items(self, ctx):
        """List all items in the shop"""
        try:
            self.c.execute("SELECT id, name, price, role_id FROM shop_items ORDER BY price")
            items = self.c.fetchall()
            
            if not items:
                return await ctx.send("❌ There are no items in the shop.")
                
            embed = discord.Embed(
                title="🛍️ Shop Items",
                description="Here are all available shop items:",
                color=discord.Color.blue()
            )
            
            for item in items:
                role = ctx.guild.get_role(item[3])
                role_status = f"✅ @{role.name}" if role else "❌ Role not found"
                embed.add_field(
                    name=f"{item[1]} - {item[2]:,} coins",
                    value=f"ID: {item[0]} | Role: {role_status}",
                    inline=False
                )
                
            await ctx.send(embed=embed)
                
        except Exception as e:
            await ctx.send(f"❌ Error listing items: {e}")
            
    @admin.command(name="updateprices")
    async def update_prices(self, ctx):
        """Update all shop prices to new balanced values"""
        try:
            # Import the update_prices function
            from utils.update_prices import update_shop_prices
            
            # Show processing message
            message = await ctx.send("⏳ Updating shop prices...")
            
            # Run the update function
            result = update_shop_prices()
            
            if result:
                embed = discord.Embed(
                    title="✅ Shop Prices Updated",
                    description="All shop prices have been updated to new balanced values.",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="New Prices",
                    value=(
                        "• Standard roles: 50,000 coins\n"
                        "• VIP role: 100,000 coins"
                    ),
                    inline=False
                )
                embed.add_field(
                    name="Economy Balance",
                    value=(
                        "• Chat rewards: 10-50 coins per message\n"
                        "• Daily rewards: 1,000-6,000 coins\n"
                        "• Days to earn a role: ~2 weeks of regular activity"
                    ),
                    inline=False
                )
                await message.edit(content=None, embed=embed)
            else:
                await message.edit(content="❌ Failed to update shop prices. Check the console for errors.")
                
        except Exception as e:
            await ctx.send(f"❌ Error updating prices: {e}")

async def setup(bot):
    await bot.add_cog(AdminTools(bot)) 