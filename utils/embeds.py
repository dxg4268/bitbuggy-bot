import discord
import datetime

def create_balance_embed(user, balance):
    """Creates an embed for displaying user balance"""
    embed = discord.Embed(
        title="💰 Balance",
        description=f"You have **{balance}** coins",
        color=discord.Color.gold()
    )
    embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    embed.set_footer(text=f"BitBuddy Economy System")
    embed.timestamp = datetime.datetime.now()
    return embed

def create_shop_embed():
    """Creates an embed for the shop"""
    embed = discord.Embed(
        title="🛍️ BitBuddy Shop",
        description="Select an item from the menu below to purchase",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Buy awesome items with your coins!")
    embed.timestamp = datetime.datetime.now()
    return embed

def create_purchase_embed(item_name, price, success=True):
    """Creates an embed for purchase confirmation/failure"""
    if success:
        embed = discord.Embed(
            title="✅ Purchase Successful",
            description=f"You purchased **{item_name}** for **{price}** coins",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="❌ Purchase Failed",
            description=f"You couldn't purchase **{item_name}** for **{price}** coins",
            color=discord.Color.red()
        )
    embed.timestamp = datetime.datetime.now()
    return embed

def create_daily_reward_embed(coins_earned, streak=None):
    """Creates an embed for daily rewards"""
    embed = discord.Embed(
        title="🎁 Daily Reward Claimed!",
        description=f"You received **{coins_earned}** coins",
        color=discord.Color.purple()
    )
    
    if streak:
        embed.add_field(name="Current Streak", value=f"**{streak}** days", inline=False)
        
    embed.set_footer(text="Come back tomorrow for more rewards!")
    embed.timestamp = datetime.datetime.now()
    return embed 