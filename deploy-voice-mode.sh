#!/bin/bash

# Deploy Voice Conversation Mode
# This script rebuilds and restarts the services with the new WebSocket support

set -e  # Exit on error

echo "============================================"
echo "  Jarvas Voice Mode - Deployment Script"
echo "============================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

cd /opt/virtualasistant

echo -e "${YELLOW}Step 1: Installing Backend Dependencies...${NC}"
docker compose exec backend pip install -r /app/requirements.txt
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backend dependencies installed${NC}"
else
    echo -e "${RED}✗ Failed to install backend dependencies${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 2: Running Database Migrations...${NC}"
docker compose exec backend python manage.py migrate
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Migrations completed${NC}"
else
    echo -e "${RED}✗ Migration failed${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 3: Collecting Static Files...${NC}"
docker compose exec backend python manage.py collectstatic --noinput
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Static files collected${NC}"
else
    echo -e "${RED}✗ Static files collection failed${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 4: Rebuilding Frontend...${NC}"
if docker compose exec frontend npm --version > /dev/null 2>&1; then
    docker compose exec frontend npm install
    docker compose exec frontend npm run build
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Frontend rebuilt${NC}"
    else
        echo -e "${RED}✗ Frontend build failed${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ npm not available in frontend container, skipping build${NC}"
    echo -e "${YELLOW}  (Frontend may be served as pre-built static files)${NC}"
fi

echo ""
echo -e "${YELLOW}Step 5: Reloading Nginx...${NC}"
docker compose exec nginx nginx -t && docker compose exec nginx nginx -s reload
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Nginx reloaded${NC}"
else
    echo -e "${RED}✗ Nginx reload failed${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 6: Restarting Backend (to use Daphne/ASGI)...${NC}"
docker compose restart backend
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backend restarted${NC}"
else
    echo -e "${RED}✗ Backend restart failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  ✓ Deployment Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Next steps:"
echo "1. Check backend logs: docker compose logs -f backend"
echo "2. Verify Redis is running: docker compose ps redis"
echo "3. Navigate to: http://localhost:1080/conversation"
echo "4. Click 'Ligar' to start voice conversation"
echo ""
echo "For troubleshooting, see: VOICE_CONVERSATION_SETUP.md"
echo ""

