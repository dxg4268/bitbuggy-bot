# BitBuddy Discord Bot

A Discord economy bot with embeds, daily rewards, admin tools, and a shop system for role rewards.

## Features

- 💰 Currency system that rewards active users
- 🎁 Daily rewards for users active for 10+ minutes (100 coins)
- 🛍️ Shop system with anime/game theme role rewards
- 👑 Admin commands with role-based permissions
- 🌈 Beautiful embeds for all responses

## Setup Instructions

### Prerequisites

- Python 3.9 or higher
- Discord Bot Token
- Server with a designated shop channel

### Installation

#### Local Development Setup

1. Clone this repository
```bash
git clone https://github.com/yourusername/bitbuddy.git
cd bitbuddy
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Set environment variables
   - Option 1: Create a `.env` file with:
   ```
   DISCORD_TOKEN=your_bot_token_here
   SHOP_CHANNEL_ID=your_shop_channel_id_here
   ```
   - Option 2: Set environment variables directly in your system

4. Run the bot
```bash
python main.py
```

## Deployment Options

### Render Deployment (Recommended)

1. Create a Render account at [render.com](https://render.com)

2. Connect your GitHub repository to Render

3. Create a new Web Service:
   - Choose the repository with your bot
   - Select "Docker" as the Environment
   - Set the following environment variables in the Render Dashboard:
     - `DISCORD_TOKEN`: Your Discord bot token
     - `SHOP_CHANNEL_ID`: Your shop channel ID

4. **IMPORTANT**: Set up persistent storage:
   - Under "Disk" section, select "Create New Disk"
   - Set size to at least 1GB
   - Set mount path to exactly: `/app/data`
   - This step is critical for database persistence!

5. Choose a plan (Free tier works for basic usage)

6. Advanced Settings:
   - Health Check Path: `/` (default)
   - Set Auto-Deploy to "Yes" if you want automatic updates

7. Click "Create Web Service" and Render will build and deploy your bot

8. Troubleshooting Render issues:
   - Check logs in the Render dashboard
   - Ensure the persistent disk is properly mounted
   - If database errors occur, you may need to manually reset:
     - Go to Shell tab in Render dashboard
     - Run: `ls -la /app/data` to verify database location
     - Run: `rm -f /app/data/shop.db` (only if needed to reset)

### Quick Deployment (Using the Script)

We've included a deployment script that simplifies managing your bot:

1. Make the script executable:
```bash
chmod +x deploy.sh
```

2. Use the script to manage your bot:
```bash
# Start the bot
./deploy.sh start

# Check logs
./deploy.sh logs

# Update the bot (pulls latest code, builds, and restarts)
./deploy.sh update

# Backup the database
./deploy.sh backup

# Stop the bot
./deploy.sh stop
```

### Manual Docker Deployment

1. Make sure Docker and Docker Compose are installed:
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo apt-get install docker-compose-plugin
```

2. Set environment variables:
```bash
# Export variables before running docker-compose
export DISCORD_TOKEN=your_token_here
export SHOP_CHANNEL_ID=your_channel_id_here
```

3. Build and start the bot:
```bash
docker-compose up -d --build
```

4. View logs:
```bash
docker-compose logs -f
```

### VPS Hosting (Manual Setup)

1. Rent a VPS from DigitalOcean, Linode, AWS, etc.
2. SSH into your VPS:
   ```bash
   ssh username@your_server_ip
   ```
3. Install Docker and Docker Compose (see above)
4. Clone your repository and configure it
5. Use the deployment script to manage your bot

### Free Oracle Cloud Always-Free Tier

Oracle Cloud offers an always-free tier ARM-based server:

1. Sign up at [Oracle Cloud](https://www.oracle.com/cloud/free/)
2. Create an Always Free VM instance (ARM Ampere A1)
3. Follow the same VPS setup instructions above

## Bot Commands

### User Commands
- `!balance` - Check your coin balance
- `!shop` - Browse and purchase items from the shop
- `!daily` - Check your daily reward status

### Admin Commands
- `!admin` - View all admin commands
- `!admin addcoins @user amount` - Add coins to a user
- `!admin removecoins @user amount` - Remove coins from a user
- `!admin addrole @role` - Add a role that can use admin commands
- `!admin listroles` - List all roles that can use admin commands
- `!admin viewbalance @user` - View another user's balance
- `!admin resetdaily @user` - Reset a user's daily reward streak
- `!admin additem name price role_id` - Add a new item to the shop
- `!admin removeitem name` - Remove an item from the shop

## Database Management

Your bot uses SQLite for data storage:

- **User balances**: Stored in the `users` table
- **Shop items**: Stored in the `shop_items` table 
- **Admin roles**: Stored in the `admin_roles` table
- **Daily rewards**: Stored in the `daily_rewards` table

The database is automatically backed up when using the deployment script's `update` or `backup` commands.

## Troubleshooting

- **Bot not responding:** Check your token and make sure the bot is online

- **Database issues on Render:**
  ```bash
  # From Render shell:
  ls -la /app/data            # Check if directory exists and permissions
  ps aux | grep python        # Verify bot is running
  cat /app/data/shop.db       # Check if database exists (will show binary)
  ```

- **Can't see shop items:** If you've updated the items but they don't appear, you may need to reset the database:
  ```bash
  # Stop the bot
  ./deploy.sh stop
  
  # Remove old database (WARNING: This deletes all user data!)
  rm -f data/shop.db
  
  # Restart the bot
  ./deploy.sh start
  ```

- **Docker issues:** Check logs with `./deploy.sh logs` or `docker-compose logs -f`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [discord.py](https://github.com/Rapptz/discord.py) - The Discord API wrapper used 