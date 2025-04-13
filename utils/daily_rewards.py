import sqlite3
import datetime
import discord
from discord.ext import commands, tasks
from utils.embeds import create_daily_reward_embed
import os
import time

class DailyRewards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = self.connect_with_retry()
        self.c = self.conn.cursor()
        self.setup_database()
        self.user_activity = {}  # Track user activity {user_id: minutes_active}
        self.check_activity.start()
        
    def connect_with_retry(self, max_retries=5, retry_delay=1):
        """Connect to the database with retry logic"""
        DB_PATH = os.getenv('DB_PATH', 'shop.db')
        retries = 0
        last_error = None
        
        while retries < max_retries:
            try:
                conn = sqlite3.connect(DB_PATH)
                print(f"DailyRewards: Successfully connected to database at {DB_PATH}")
                return conn
            except sqlite3.Error as e:
                last_error = e
                retries += 1
                print(f"DailyRewards: Database connection error (attempt {retries}/{max_retries}): {e}")
                if retries < max_retries:
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
        
        # If we get here, all retries failed
        raise last_error or sqlite3.Error("DailyRewards: Failed to connect to database after multiple attempts")
        
    def setup_database(self):
        """Set up the daily rewards table"""
        try:
            self.c.execute('''CREATE TABLE IF NOT EXISTS daily_rewards 
                           (user_id INTEGER PRIMARY KEY, 
                            last_claim TIMESTAMP,
                            streak INTEGER DEFAULT 0)''')
            self.conn.commit()
            print("DailyRewards: Database tables initialized")
        except sqlite3.Error as e:
            print(f"DailyRewards: Error setting up database: {e}")
        
    def cog_unload(self):
        self.check_activity.cancel()
        self.conn.close()
        
    @tasks.loop(minutes=1)
    async def check_activity(self):
        """Check user activity every minute"""
        # Process users who have been active for 10+ minutes
        for user_id, minutes in list(self.user_activity.items()):
            if minutes >= 10:
                # User has been active for 10+ minutes, eligible for daily reward
                self.user_activity.pop(user_id)  # Remove from tracking
                
                try:
                    # Check if they already claimed today
                    today = datetime.datetime.now().date()
                    self.c.execute("SELECT last_claim, streak FROM daily_rewards WHERE user_id = ?", (user_id,))
                    result = self.c.fetchone()
                    
                    if not result or datetime.datetime.fromisoformat(result[0]).date() < today:
                        # Eligible for reward
                        await self.give_daily_reward(user_id)
                except Exception as e:
                    print(f"DailyRewards: Error checking activity for user {user_id}: {e}")
    
    @check_activity.before_loop
    async def before_check_activity(self):
        await self.bot.wait_until_ready()
        
    async def track_user_activity(self, user_id):
        """Track a user's activity"""
        if user_id not in self.user_activity:
            self.user_activity[user_id] = 0
        else:
            self.user_activity[user_id] += 1
            
    async def give_daily_reward(self, user_id):
        """Give daily reward to a user"""
        reward_amount = 100
        today = datetime.datetime.now().isoformat()
        
        # Get user's current streak
        self.c.execute("SELECT streak FROM daily_rewards WHERE user_id = ?", (user_id,))
        result = self.c.fetchone()
        
        if result:
            # User exists, update their streak
            streak = result[0] + 1
            self.c.execute("UPDATE daily_rewards SET last_claim = ?, streak = ? WHERE user_id = ?", 
                          (today, streak, user_id))
        else:
            # New user, set initial streak
            streak = 1
            self.c.execute("INSERT INTO daily_rewards (user_id, last_claim, streak) VALUES (?, ?, ?)", 
                          (user_id, today, streak))
        
        # Add coins to user balance
        self.c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = self.c.fetchone()
        
        if result:
            new_balance = result[0] + reward_amount
            self.c.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        else:
            self.c.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, reward_amount))
            
        self.conn.commit()
        
        # Try to send a DM to the user if possible
        user = self.bot.get_user(user_id)
        if user:
            try:
                embed = create_daily_reward_embed(reward_amount, streak)
                await user.send(embed=embed)
            except:
                pass  # User might have DMs closed, that's ok
                
    @commands.command(name="daily")
    async def daily_status(self, ctx):
        """Check your daily reward status"""
        user_id = ctx.author.id
        today = datetime.datetime.now().date()
        
        self.c.execute("SELECT last_claim, streak FROM daily_rewards WHERE user_id = ?", (user_id,))
        result = self.c.fetchone()
        
        if not result:
            embed = discord.Embed(
                title="🎁 Daily Reward",
                description="You haven't claimed any daily rewards yet.\nBe active for at least 10 minutes to earn your reward!",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Active = sending messages or using voice channels")
        else:
            last_claim_date = datetime.datetime.fromisoformat(result[0]).date()
            streak = result[1]
            
            if last_claim_date >= today:
                embed = discord.Embed(
                    title="🎁 Daily Reward",
                    description="You've already claimed your daily reward today!",
                    color=discord.Color.gold()
                )
                embed.add_field(name="Current Streak", value=f"**{streak}** days")
                embed.add_field(name="Next Reward", value="Tomorrow")
            else:
                embed = discord.Embed(
                    title="🎁 Daily Reward",
                    description="You're eligible to claim your daily reward!\nBe active for at least 10 minutes to claim it.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Current Streak", value=f"**{streak}** days")
                
        embed.timestamp = datetime.datetime.now()
        await ctx.send(embed=embed)
        
    @commands.Cog.listener()
    async def on_message(self, message):
        """Track activity when users send messages"""
        if not message.author.bot:
            await self.track_user_activity(message.author.id)
            
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Track activity when users use voice channels"""
        if not member.bot:
            if before.channel is None and after.channel is not None:
                # User joined a voice channel
                await self.track_user_activity(member.id)

async def setup(bot):
    await bot.add_cog(DailyRewards(bot)) 