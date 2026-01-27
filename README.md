# IB Portfolio Tracker - MCP Server

An MCP (Model Context Protocol) server that connects Claude AI to your Interactive Brokers account for real-time portfolio tracking, financial news, and sentiment analysis.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## What Can You Do?

Once set up, you can ask Claude things like:

- "What's my portfolio value?"
- "Show my positions with P&L"
- "Give me a full news analysis for NVDA" (combines IB + Finnhub + sentiment)
- "What's the sentiment around Tesla?"
- "Show historical data for SPY"
- "What news providers are available from IB?"

All responses come directly from your Interactive Brokers account, IB news feeds (Reuters, Dow Jones, etc.), and optionally Finnhub API.

---

## Quick Start

### Prerequisites

- **macOS, Linux, or Windows**
- **Python 3.10+** installed
- **Interactive Brokers account**
- **Claude Desktop** or **Claude Code (VS Code)**

### Step 1: Download IB Gateway

IB Gateway is a lightweight app that allows API access to your IBKR account.

1. Download from: https://www.interactivebrokers.com/en/trading/ibgateway-stable.php
2. Install and log in with your IBKR credentials
3. Configure API settings:
   - Go to **Configure → Settings → API → Settings**
   - Set **Socket port** to `4001`
   - Check **Read-Only API** (recommended for safety)
4. Keep IB Gateway running whenever you want to use the portfolio features

> **Note:** IBKR Desktop app does NOT support API connections. You need IB Gateway or TWS.

### Step 2: Get a Finnhub API Key (Optional)

Finnhub provides additional news and social sentiment data. **This is optional** - IB native news works without it.

1. Sign up at: https://finnhub.io/register
2. Copy your API key from the dashboard
3. Free tier: 60 requests/minute (plenty for personal use)

### Step 3: Install the MCP Server

```bash
# Clone or download this repository
git clone https://github.com/vinbg/ib-mcp-server.git
cd ib-mcp-server

# Run the setup script
# Mac/Linux:
chmod +x setup.sh
./setup.sh

# Windows:
setup.bat
```

The setup script will:
- Create a Python virtual environment
- Install all dependencies
- Guide you through configuration
- Test your connections

### Step 4: Configure Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ib-portfolio": {
      "command": "/FULL/PATH/TO/ib-mcp-server/.venv/bin/python",
      "args": ["-m", "ib_mcp.server"],
      "cwd": "/FULL/PATH/TO/ib-mcp-server"
    }
  }
}
```

**Replace `/FULL/PATH/TO/` with your actual path!**

Then restart Claude Desktop (Cmd+Q, then reopen).

---

## Optional: Add LunarCrush for Crypto Sentiment

LunarCrush provides social sentiment data for cryptocurrencies. To add it alongside this server:

1. Get an API key at: https://lunarcrush.com/developers
2. Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "ib-portfolio": {
      "command": "/FULL/PATH/TO/ib-mcp-server/.venv/bin/python",
      "args": ["-m", "ib_mcp.server"],
      "cwd": "/FULL/PATH/TO/ib-mcp-server"
    },
    "LunarCrush": {
      "type": "http",
      "url": "https://lunarcrush.ai/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_LUNARCRUSH_API_KEY"
      }
    }
  }
}
```

Now you can ask Claude about crypto social sentiment alongside your IBKR portfolio!

---

## Available Tools (22 total)

### Comprehensive News (RECOMMENDED)
| Tool | Description |
|------|-------------|
| `get_comprehensive_news` | **All-in-one news analysis** - combines IB news, Finnhub news, social sentiment, insider sentiment, and AI-analyzed scores |

### Portfolio Tools (requires IB Gateway)
| Tool | Description |
|------|-------------|
| `get_account_summary` | Net liquidation value, buying power, cash, margin |
| `get_positions` | All positions with quantities, cost basis, P&L |
| `get_portfolio_pnl` | Daily, unrealized, and realized P&L breakdown |
| `get_position_details` | Detailed info for a specific symbol |
| `get_open_orders` | List pending orders |
| `get_executions` | Recent trade fills |

### Market Data Tools (requires IB Gateway)
| Tool | Description |
|------|-------------|
| `get_quote` | Real-time/delayed quotes (bid, ask, last, volume) |
| `get_historical_data` | OHLCV historical bars |
| `get_contract_details` | Symbol info, trading hours |
| `search_symbols` | Find contracts by name |

### IB Native News Tools (requires IB Gateway)
| Tool | Description |
|------|-------------|
| `get_ib_news_providers` | List available news sources (Reuters, Dow Jones, etc.) |
| `get_ib_news` | Get historical news from IB for a symbol |
| `get_ib_news_article` | Get full article text by article ID |

### Finnhub News & Sentiment Tools (requires Finnhub API)
| Tool | Description |
|------|-------------|
| `search_news` | Search by symbol or keyword |
| `get_company_news` | Company-specific headlines |
| `get_market_news` | General market news |
| `get_social_sentiment` | Reddit/Twitter sentiment metrics |
| `get_insider_sentiment` | Insider trading signals |

### Sentiment Analysis Tools
| Tool | Description |
|------|-------------|
| `analyze_news_sentiment` | AI sentiment analysis on news |
| `analyze_text_sentiment` | Analyze any custom text |

### Utility Tools
| Tool | Description |
|------|-------------|
| `check_connection_status` | Check IB and API connections |

---

## Configuration

All settings are in the `.env` file:

```bash
# Interactive Brokers Connection
IB_HOST=127.0.0.1
IB_PORT=4001              # 4001=Gateway Paper, 4002=Gateway Live

# News API
FINNHUB_API_KEY=your_finnhub_key_here

# Sentiment Model
SENTIMENT_MODEL=vader     # "vader" (fast) or "finbert" (accurate, 500MB model)

# Logging
LOG_LEVEL=INFO
```

### Port Reference

| Port | Application | Mode |
|------|-------------|------|
| 4001 | IB Gateway | Paper Trading |
| 4002 | IB Gateway | Live Trading |
| 7497 | TWS | Paper Trading |
| 7496 | TWS | Live Trading |

---

## Security

This server is **READ-ONLY** by default:

- No order placement capabilities
- No account modification
- API keys stored locally in `.env` (never committed to git)
- Works with IB's "Read-Only API" setting

Your credentials never leave your machine. The MCP server runs locally and communicates only with:
- IB Gateway on localhost
- Finnhub API (for news)

---

## Troubleshooting

### "Cannot connect to IB Gateway"

1. **Is IB Gateway running?** Check your dock/taskbar
2. **Correct port?** Verify port in IB Gateway matches your `.env`
3. **API enabled?** In IB Gateway: Configure → Settings → API → Settings
4. **Firewall?** Ensure localhost connections aren't blocked

### "Invalid API key" (Finnhub)

1. Check your key at https://finnhub.io/dashboard
2. Verify it's correctly copied to `.env`
3. Free tier limit: 60 requests/minute

### "Tool not found" in Claude

1. Restart Claude Desktop completely (Cmd+Q)
2. Check the config file path is correct
3. Verify Python path: `which python3` in terminal

### Test the connection manually

```bash
cd ib-mcp-server
source .venv/bin/activate
python -c "
from ib_async import IB
import asyncio

async def test():
    ib = IB()
    await ib.connectAsync('127.0.0.1', 4001, clientId=99)
    print('Connected!')
    print('Accounts:', ib.managedAccounts())
    ib.disconnect()

asyncio.run(test())
"
```

---

## Project Structure

```
ib-mcp-server/
├── setup.sh              # Mac/Linux setup script
├── setup.bat             # Windows setup script
├── pyproject.toml        # Python dependencies
├── .env.example          # Configuration template
├── .env                  # Your configuration (gitignored)
├── README.md             # This file
├── claude.md             # Claude Code documentation
└── src/ib_mcp/
    ├── server.py         # MCP server entry point
    ├── config.py         # Configuration management
    └── clients/
        ├── ib_client.py    # Interactive Brokers API
        ├── news_client.py  # Finnhub API
        └── sentiment.py    # Sentiment analysis
```

---

## License

MIT License - feel free to use, modify, and share.

---

## Disclaimer

This software is for informational purposes only. It does not constitute financial advice. Always verify information independently before making investment decisions. The authors are not responsible for any financial losses incurred through the use of this software.
