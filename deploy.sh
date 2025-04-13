#!/bin/bash
# BitBuddy Discord Bot Deployment Script

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}BitBuddy Discord Bot - Deployment Script${NC}"
echo "========================================"

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating from example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}Please edit .env file with your actual token and channel ID before continuing.${NC}"
        echo -e "${YELLOW}Press Enter to continue after editing, or Ctrl+C to cancel.${NC}"
        read
    else
        echo -e "${RED}Error: .env.example file not found. Please create a .env file manually.${NC}"
        exit 1
    fi
fi

# Check action parameter
ACTION=$1
if [ -z "$ACTION" ]; then
    echo "Usage: $0 [start|stop|restart|logs|update|backup]"
    echo ""
    echo "Commands:"
    echo "  start   - Start the bot"
    echo "  stop    - Stop the bot"
    echo "  restart - Restart the bot"
    echo "  logs    - Show bot logs"
    echo "  update  - Update to latest code and restart"
    echo "  backup  - Backup the database"
    exit 1
fi

# Execute requested action
case $ACTION in
    start)
        echo -e "${GREEN}Starting BitBuddy...${NC}"
        docker-compose up -d
        echo -e "${GREEN}Bot started successfully!${NC}"
        ;;
    stop)
        echo -e "${YELLOW}Stopping BitBuddy...${NC}"
        docker-compose down
        echo -e "${GREEN}Bot stopped successfully!${NC}"
        ;;
    restart)
        echo -e "${YELLOW}Restarting BitBuddy...${NC}"
        docker-compose down
        docker-compose up -d
        echo -e "${GREEN}Bot restarted successfully!${NC}"
        ;;
    logs)
        echo -e "${GREEN}Showing logs (Ctrl+C to exit):${NC}"
        docker-compose logs -f
        ;;
    update)
        echo -e "${YELLOW}Updating BitBuddy...${NC}"
        
        # Create backup first
        BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).db"
        echo -e "${GREEN}Creating backup: $BACKUP_FILE${NC}"
        
        if [ -d "data" ]; then
            cp data/shop.db "backups/$BACKUP_FILE" 2>/dev/null || echo -e "${YELLOW}Couldn't create local backup.${NC}"
        else
            mkdir -p backups
            docker cp bitbuddy:/app/data/shop.db "backups/$BACKUP_FILE" 2>/dev/null || echo -e "${YELLOW}Couldn't create backup from container.${NC}"
        fi
        
        # Pull latest code if using git
        if [ -d .git ]; then
            echo -e "${GREEN}Pulling latest code...${NC}"
            git pull
        fi
        
        # Rebuild and restart
        echo -e "${GREEN}Rebuilding and restarting...${NC}"
        docker-compose down
        docker-compose up -d --build
        
        echo -e "${GREEN}Bot updated successfully!${NC}"
        ;;
    backup)
        echo -e "${GREEN}Creating database backup...${NC}"
        
        # Create backups directory if it doesn't exist
        mkdir -p backups
        
        # Backup filename with timestamp
        BACKUP_FILE="backups/shop_$(date +%Y%m%d_%H%M%S).db"
        
        # Copy from container or local data directory
        if docker ps | grep -q bitbuddy; then
            docker cp bitbuddy:/app/data/shop.db "$BACKUP_FILE"
        elif [ -f "data/shop.db" ]; then
            cp data/shop.db "$BACKUP_FILE"
        else
            echo -e "${RED}Error: Could not find database to backup.${NC}"
            exit 1
        fi
        
        echo -e "${GREEN}Backup created: $BACKUP_FILE${NC}"
        ;;
    *)
        echo -e "${RED}Unknown command: $ACTION${NC}"
        echo "Usage: $0 [start|stop|restart|logs|update|backup]"
        exit 1
        ;;
esac

exit 0 