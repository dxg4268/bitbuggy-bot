import discord
import datetime

def create_balance_embed(user, balance):
    """Create an embed for displaying user balance"""
    embed = discord.Embed(
        title="💰 Wallet Balance",
        description=f"{user.mention}, you have **{balance:,}** coins in your wallet.",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.set_footer(text="Earn more coins by chatting and claiming daily rewards!")
    embed.timestamp = datetime.datetime.now()
    return embed

def create_shop_embed():
    """Create an embed for displaying the shop"""
    embed = discord.Embed(
        title="🛍️ BitBuddy Shop",
        description="Buy special roles with your coins!",
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="How to buy",
        value="Select an item from the dropdown menu below to purchase it.",
        inline=False
    )
    embed.add_field(
        name="Earning coins",
        value="• Chat in the server to earn 10-50 coins per message\n• Claim daily rewards (up to 6,000 coins with streak!)\n• Standard roles cost 50,000 coins\n• VIP role costs 100,000 coins",
        inline=False
    )
    embed.add_field(
        name="Time to earn",
        value="With regular activity, you can earn a standard role in about 2 weeks and the VIP role in about a month. Stay active!",
        inline=False
    )
    embed.set_footer(text="Prices are subject to change.")
    return embed

def create_purchase_embed(item_name, price, success=True):
    """Create an embed for purchase result"""
    if success:
        embed = discord.Embed(
            title="✅ Purchase Successful!",
            description=f"You have successfully purchased **{item_name}** for **{price:,}** coins!",
            color=discord.Color.green()
        )
        embed.set_footer(text="Enjoy your new role!")
    else:
        embed = discord.Embed(
            title="❌ Purchase Failed",
            description=f"You don't have enough coins to purchase **{item_name}** ({price:,} coins).",
            color=discord.Color.red()
        )
        embed.set_footer(text="Keep chatting to earn more coins!")
    return embed

def create_daily_reward_embed(amount, streak):
    """Create an embed for daily reward notification"""
    if streak > 1:
        title = f"🎁 Daily Reward Claimed! (Streak: {streak} days)"
        description = f"You've received **{amount:,}** coins for your daily activity!"
        footer = f"Come back tomorrow to keep your streak going!"
    else:
        title = "🎁 Daily Reward Claimed!"
        description = f"You've received **{amount:,}** coins for your daily activity!"
        footer = "Come back tomorrow to start a streak for bonus rewards!"
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.green()
    )
    embed.add_field(
        name="Streak Rewards",
        value="Keep your streak going for even more coins each day!",
        inline=False
    )
    embed.set_footer(text=footer)
    return embed 