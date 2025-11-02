#!/bin/bash
#
# Restart Options Income Screener API Server
# Cleanly stops and restarts the Node.js API server
#

# Colors for output
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${YELLOW}================================================${NC}"
echo -e "${YELLOW}  Options Income Screener - Restart API${NC}"
echo -e "${YELLOW}================================================${NC}"

# Stop the server
"$SCRIPT_DIR/stop_api.sh"

# Wait a moment
sleep 2

# Start the server
"$SCRIPT_DIR/start_api.sh"
