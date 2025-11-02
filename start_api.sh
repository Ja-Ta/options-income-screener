#!/bin/bash
#
# Start Options Income Screener API Server
# Simple manual startup script for the Node.js API
#

set -e

# Configuration
PROJECT_DIR="/home/oisadm/development/options-income-screener"
NODE_DIR="$PROJECT_DIR/node_ui"
LOG_FILE="/tmp/api_server.log"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}================================================${NC}"
echo -e "${YELLOW}  Options Income Screener - API Startup${NC}"
echo -e "${YELLOW}================================================${NC}"

# Kill any existing processes on port 3000
echo -e "\n${YELLOW}🔍 Checking for existing processes on port 3000...${NC}"
if lsof -ti:3000 > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Found existing process, stopping it...${NC}"
    lsof -ti:3000 | xargs kill -9 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}✅ Stopped existing process${NC}"
else
    echo -e "${GREEN}✅ Port 3000 is free${NC}"
fi

# Start the server
echo -e "\n${YELLOW}🚀 Starting API server...${NC}"
cd "$NODE_DIR"

# Start in background and redirect output to log
nohup node src/server.js > "$LOG_FILE" 2>&1 &
SERVER_PID=$!

# Wait a moment for server to start
sleep 3

# Check if server is running
if ps -p $SERVER_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Server started successfully!${NC}"
    echo -e "${GREEN}   PID: $SERVER_PID${NC}"
    echo -e "${GREEN}   Logs: $LOG_FILE${NC}"

    # Test the health endpoint
    if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Health check passed${NC}"
        echo -e "\n${GREEN}================================================${NC}"
        echo -e "${GREEN}  Server is running on http://0.0.0.0:3000${NC}"
        echo -e "${GREEN}  API Docs: http://0.0.0.0:3000/api${NC}"
        echo -e "${GREEN}  Health:   http://0.0.0.0:3000/api/health${NC}"
        echo -e "${GREEN}================================================${NC}"
        echo -e "\n${YELLOW}To view logs:${NC} tail -f $LOG_FILE"
        echo -e "${YELLOW}To stop:${NC} kill $SERVER_PID"
    else
        echo -e "${RED}⚠️  Server started but health check failed${NC}"
        echo -e "${YELLOW}Check logs:${NC} tail $LOG_FILE"
    fi
else
    echo -e "${RED}❌ Failed to start server${NC}"
    echo -e "${YELLOW}Check logs:${NC} tail $LOG_FILE"
    exit 1
fi
