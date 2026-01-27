#!/bin/bash

# IB Portfolio MCP Server - Setup Script
# This script will set up everything you need to run the MCP server

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        IB Portfolio Tracker - MCP Server Setup               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}Step 1: Checking Python installation...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓ Found $PYTHON_VERSION${NC}"
else
    echo -e "${RED}✗ Python 3 not found. Please install Python 3.10 or higher.${NC}"
    echo "  Download from: https://www.python.org/downloads/"
    exit 1
fi

echo ""
echo -e "${BLUE}Step 2: Creating virtual environment...${NC}"
if [ -d ".venv" ]; then
    echo -e "${YELLOW}  Virtual environment already exists, skipping...${NC}"
else
    python3 -m venv .venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

echo ""
echo -e "${BLUE}Step 3: Installing dependencies...${NC}"
source .venv/bin/activate
pip install --upgrade pip -q
pip install -e . -q
echo -e "${GREEN}✓ Dependencies installed${NC}"

echo ""
echo -e "${BLUE}Step 4: Configuring environment...${NC}"

if [ -f ".env" ]; then
    echo -e "${YELLOW}  .env file already exists${NC}"
    read -p "  Overwrite? (y/N): " overwrite
    if [[ ! "$overwrite" =~ ^[Yy]$ ]]; then
        echo "  Keeping existing .env file"
    else
        rm .env
    fi
fi

if [ ! -f ".env" ]; then
    echo ""
    echo -e "${YELLOW}IB Gateway/TWS Port Configuration:${NC}"
    echo "  4001 = IB Gateway Paper Trading (recommended)"
    echo "  4002 = IB Gateway Live Trading"
    echo "  7497 = TWS Paper Trading"
    echo "  7496 = TWS Live Trading"
    read -p "  Enter port [4001]: " IB_PORT
    IB_PORT=${IB_PORT:-4001}

    # Create .env file
    cat > .env << EOF
# Interactive Brokers Connection
IB_HOST=127.0.0.1
IB_PORT=$IB_PORT
IB_CLIENT_ID=1

# Logging
LOG_LEVEL=INFO
EOF

    echo -e "${GREEN}✓ Configuration saved to .env${NC}"
fi

echo ""
echo -e "${BLUE}Step 5: Testing IB Gateway connection...${NC}"
python3 -c "
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
port = int(os.getenv('IB_PORT', 4001))

async def test():
    from ib_async import IB
    ib = IB()
    try:
        await ib.connectAsync('127.0.0.1', port, clientId=99, timeout=5)
        accounts = ib.managedAccounts()
        print(f'✓ Connected to IB Gateway (Account: {accounts[0] if accounts else \"N/A\"})')
        ib.disconnect()
    except Exception as e:
        print(f'⚠ IB Gateway not running or not accessible on port {port}')
        print(f'  Make sure IB Gateway is running before using portfolio features')

asyncio.run(test())
" 2>/dev/null || echo -e "${YELLOW}⚠ Could not test IB connection${NC}"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Setup Complete!                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo ""
echo "1. Make sure IB Gateway is running"
echo "   Download: https://www.interactivebrokers.com/en/trading/ibgateway-stable.php"
echo ""
echo "2. Add to Claude Desktop config:"
echo "   File: ~/Library/Application Support/Claude/claude_desktop_config.json"
echo ""
echo '   {
     "mcpServers": {
       "ib-portfolio": {
         "command": "'$SCRIPT_DIR'/.venv/bin/python",
         "args": ["-m", "ib_mcp.server"],
         "cwd": "'$SCRIPT_DIR'"
       }
     }
   }'
echo ""
echo "3. Restart Claude Desktop (Cmd+Q, then reopen)"
echo ""
echo "4. Ask Claude: \"What's my portfolio value?\""
echo ""
echo -e "${BLUE}For troubleshooting, see README.md${NC}"
