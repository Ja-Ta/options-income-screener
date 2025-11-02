#!/bin/bash
#
# Stop Options Income Screener API Server
# Cleanly stops the Node.js API server
#

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}================================================${NC}"
echo -e "${YELLOW}  Options Income Screener - Stop API${NC}"
echo -e "${YELLOW}================================================${NC}"

# Find process on port 3000
echo -e "\n${YELLOW}🔍 Looking for server on port 3000...${NC}"

PID=$(lsof -ti:3000 2>/dev/null)

if [ -z "$PID" ]; then
    echo -e "${GREEN}✅ No server running on port 3000${NC}"
    exit 0
fi

echo -e "${YELLOW}📍 Found process: PID $PID${NC}"

# Try graceful shutdown first (SIGTERM)
echo -e "${YELLOW}⏹️  Attempting graceful shutdown...${NC}"
kill -15 $PID 2>/dev/null

# Wait up to 5 seconds for graceful shutdown
for i in {1..5}; do
    sleep 1
    if ! ps -p $PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Server stopped gracefully${NC}"
        exit 0
    fi
    echo -e "${YELLOW}   Waiting... ($i/5)${NC}"
done

# Force kill if still running
echo -e "${YELLOW}⚠️  Graceful shutdown failed, forcing...${NC}"
kill -9 $PID 2>/dev/null
sleep 1

if ! ps -p $PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Server stopped (forced)${NC}"
else
    echo -e "${RED}❌ Failed to stop server${NC}"
    exit 1
fi
