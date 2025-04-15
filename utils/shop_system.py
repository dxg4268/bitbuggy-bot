import discord
from discord.ext import commands
import sqlite3
from utils.embeds import create_shop_embed, create_purchase_embed
import os
import time
import traceback
from utils.db_monitor import check_db_status

class ShopView(discord.ui.View):
    def __init__(self, user, ctx, shop_items):
        super().__init__()
        self.user = user
        self.ctx = ctx
        self.shop_items = shop_items

        options = [
            discord.SelectOption(label=item[1], description=f"{item[2]} points", value=str(item[0]))
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
                description=f"Are you sure you want to buy **{item_name}** for **{item_price}** points?",
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

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("You can't confirm someone else's purchase.", ephemeral=True)
            return

        item_name = self.item[1]
        item_price = self.item[2]
        role_id = self.item[3]

        try:
            conn = sqlite3.connect(os.getenv('DB_PATH', 'shop.db'))
            c = conn.cursor()
            
            c.execute("SELECT balance FROM users WHERE user_id = ?", (self.user.id,))
            result = c.fetchone()
            
            if not result or result[0] < item_price:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="❌ Purchase Failed",
                        description=f"Insufficient balance to purchase {item_name}",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
            
            new_balance = result[0] - item_price
            c.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, self.user.id))
            conn.commit()
            
            role = self.ctx.guild.get_role(role_id)
            if role:
                await self.user.add_roles(role)
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="✅ Purchase Successful",
                        description=f"You have purchased {item_name} for {item_price} points!",
                        color=discord.Color.green()
                    ),
                    ephemeral=True
                )
            else:
                await interaction.response.send_message("Role not found. Please contact an admin.", ephemeral=True)
            
        except Exception as e:
            print(f"Purchase error: {str(e)}")
            traceback.print_exc()
            await interaction.response.send_message("There was an error processing your purchase. Please try again later.", ephemeral=True)
        finally:
            if 'conn' in locals():
                conn.close()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == self.user:
            await interaction.response.send_message("❌ Purchase cancelled.", ephemeral=True)

class ShopSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = os.getenv('DB_PATH', 'shop.db')
        
        # Initialize with bot attributes
        self.shop_channel_id = bot.shop_channel_id
        self.command_channels = bot.command_channels
        
        print(f"ShopSystem: Initialized with shop channel ID: {self.shop_channel_id}")
        print(f"ShopSystem: Command channels: {self.command_channels}")
        print(f"ShopSystem: Bot command prefix: {bot.command_prefix}")

    def verify_channel_permissions(self, channel):
        """Verify bot has necessary permissions in the channel"""
        if not channel:
            print("Channel verification failed: channel is None")
            return False
            
        permissions = channel.permissions_for(channel.guild.me)
        required_permissions = [
            permissions.send_messages,
            permissions.read_messages,
            permissions.embed_links,
            permissions.attach_files
        ]
        
        has_permissions = all(required_permissions)
        if not has_permissions:
            print(f"Missing permissions in channel {channel.id}:")
            if not permissions.send_messages:
                print("- Send Messages")
            if not permissions.read_messages:
                print("- Read Messages")
            if not permissions.embed_links:
                print("- Embed Links")
            if not permissions.attach_files:
                print("- Attach Files")
        
        return has_permissions

    def connect_with_retry(self, max_retries=5, retry_delay=2):
        """Establish database connection with retry logic"""
        retries = 0
        last_error = None
        
        while retries < max_retries:
            try:
                conn = sqlite3.connect(self.db_path)
                return conn
            except sqlite3.Error as e:
                last_error = e
                retries += 1
                if retries < max_retries:
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
        
        # If all retries fail, run diagnostics
        check_db_status()
        raise last_error or sqlite3.Error("Failed to connect to database after multiple attempts")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def updateprice(self, ctx, item_name: str, new_price: int):
        """Update the price of an item in the shop"""
        print(f"\nUpdateprice command called:")
        print(f"- Channel ID: {ctx.channel.id}")
        print(f"- Author: {ctx.author.name}")
        print(f"- Command channels: {self.command_channels}")
        print(f"- Message content: {ctx.message.content}")
        
        if not self.command_channels:
            print("Command rejected: No command channels configured")
            return await ctx.send("❌ Command channels not configured. Please contact an administrator.")
            
        if ctx.channel.id not in self.command_channels:
            print(f"Command rejected: Channel {ctx.channel.id} not in command channels")
            return await ctx.send(f"❌ This command can only be used in designated command channels: {', '.join(str(c) for c in self.command_channels)}")
        
        if not self.verify_channel_permissions(ctx.channel):
            print("Command rejected: Missing permissions")
            return await ctx.send("❌ Bot does not have required permissions in this channel.")
        
        print("Command accepted, processing...")
        try:
            conn = self.connect_with_retry()
            c = conn.cursor()
            
            # Update the price
            c.execute("UPDATE shop_items SET price = ? WHERE name = ?", (new_price, item_name))
            if c.rowcount == 0:
                print(f"Item '{item_name}' not found")
                await ctx.send(f"❌ Item '{item_name}' not found in the shop.")
                return
            
            conn.commit()
            print(f"Price updated successfully: {item_name} -> {new_price}")
            await ctx.send(f"✅ Updated price of '{item_name}' to {new_price} points.")
            
            # Update the shop UI
            await self.update_shop_ui()
            
        except sqlite3.Error as e:
            print(f"Database error: {str(e)}")
            await ctx.send(f"❌ Database error: {str(e)}")
            check_db_status()
        finally:
            if 'conn' in locals():
                conn.close()

    async def update_shop_ui(self):
        """Update the shop UI in the designated channel"""
        if not self.shop_channel_id:
            print("Shop channel ID not set")
            return
            
        try:
            channel = self.bot.get_channel(self.shop_channel_id)
            if not channel:
                print(f"Shop channel {self.shop_channel_id} not found")
                return
            
            # Delete old shop message
            async for message in channel.history(limit=1):
                await message.delete()
            
            # Create and send new shop message
            embed = await self.create_shop_embed()
            if embed:
                await channel.send(embed=embed)
            
        except Exception as e:
            print(f"Error updating shop UI: {str(e)}")
            traceback.print_exc()

    async def create_shop_embed(self):
        """Create the shop embed with current prices"""
        try:
            conn = self.connect_with_retry()
            c = conn.cursor()
            
            c.execute("SELECT COUNT(*) FROM shop_items")
            item_count = c.fetchone()[0]
            
            embed = discord.Embed(
                title="🏪 Shop",
                description="Welcome to the shop! Use the dropdown menu below to browse and purchase items.",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="How to Shop",
                value="1. Select an item from the dropdown menu\n2. Review the item details\n3. Click Confirm to purchase or Cancel to abort",
                inline=False
            )
            
            embed.add_field(
                name="Available Items",
                value=f"There are currently {item_count} items available for purchase.",
                inline=False
            )
            
            embed.set_footer(text="All purchases are final. Please ensure you have enough points before confirming.")
            
            return embed
            
        except Exception as e:
            print(f"Error creating shop embed: {str(e)}")
            traceback.print_exc()
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    @commands.command()
    async def shop(self, ctx):
        """Display the shop"""
        print(f"\nShop command called:")
        print(f"- Channel ID: {ctx.channel.id}")
        print(f"- Author: {ctx.author.name}")
        print(f"- Command channels: {self.command_channels}")
        print(f"- Message content: {ctx.message.content}")
        
        if not self.command_channels:
            print("Command rejected: No command channels configured")
            return await ctx.send("❌ Command channels not configured. Please contact an administrator.")
            
        if ctx.channel.id not in self.command_channels:
            print(f"Command rejected: Channel {ctx.channel.id} not in command channels")
            return await ctx.send(f"❌ This command can only be used in designated command channels: {', '.join(str(c) for c in self.command_channels)}")
        
        if not self.verify_channel_permissions(ctx.channel):
            print("Command rejected: Missing permissions")
            return await ctx.send("❌ Bot does not have required permissions in this channel.")
        
        print("Command accepted, processing...")
        try:
            conn = self.connect_with_retry()
            c = conn.cursor()
            
            c.execute("SELECT id, name, price, role_id FROM shop_items")
            shop_items = c.fetchall()
            
            if not shop_items:
                await ctx.send("The shop is currently empty!")
                return
            
            embed = await self.create_shop_embed()
            view = ShopView(ctx.author, ctx, shop_items)
            await ctx.send(embed=embed, view=view)
            
        except Exception as e:
            print(f"Error displaying shop: {str(e)}")
            traceback.print_exc()
            await ctx.send("❌ There was an error accessing the shop. Please try again later.")
        finally:
            if 'conn' in locals():
                conn.close()

async def setup(bot):
    await bot.add_cog(ShopSystem(bot))
