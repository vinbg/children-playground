# IB Portfolio Tracker - MCP Server

An MCP (Model Context Protocol) server that connects Claude AI to Interactive Brokers accounts for real-time portfolio tracking, financial news retrieval, and sentiment analysis.

## Project Overview

This server enables conversational portfolio management through Claude. Users can query their investment portfolio, get market data, and analyze financial news sentiment through natural language.

**Key capabilities:**
- Real-time portfolio tracking and P&L monitoring
- Market quotes and historical data
- Financial news aggregation (via Finnhub)
- Sentiment analysis (VADER and FinBERT models)
- Social media and insider trading sentiment
- Read-only access (no order placement for safety)

## Tech Stack

- **Language:** Python 3.10+
- **Framework:** MCP SDK (Model Context Protocol)
- **IB Integration:** ib-async library
- **HTTP:** aiohttp for async requests
- **Validation:** Pydantic
- **Caching:** cachetools with TTL support

## Project Structure

```
ib-mcp-server/
├── src/ib_mcp/              # Main source code
│   ├── server.py            # MCP server entry point & tool handlers
│   ├── config.py            # Configuration management
│   └── clients/             # API client modules
│       ├── ib_client.py     # Interactive Brokers API wrapper
│       ├── news_client.py   # Finnhub news API client
│       └── sentiment.py     # Sentiment analysis (VADER + FinBERT)
├── .env.example             # Configuration template
├── pyproject.toml           # Python project config
├── setup.sh                 # Mac/Linux setup script
└── setup.bat                # Windows setup script
```

## Available Tools (22 total)

### Portfolio (6 tools)
- `get_account_summary` - Net liquidation value, buying power, cash, margin
- `get_positions` - All positions with quantities, cost basis, P&L
- `get_portfolio_pnl` - Daily, unrealized, and realized P&L breakdown
- `get_position_details` - Detailed info for specific symbol
- `get_open_orders` - List pending orders
- `get_executions` - Recent trade fills/executions

### Market Data (4 tools)
- `get_quote` - Real-time quotes (bid, ask, last, volume)
- `get_historical_data` - OHLCV historical bars
- `get_contract_details` - Symbol info, exchange, trading hours
- `search_symbols` - Find contracts by name

### Comprehensive News (1 tool) - RECOMMENDED
- `get_comprehensive_news` - **All-in-one news analysis** combining:
  - IB news (Reuters, Dow Jones, Briefing.com)
  - Finnhub news (if configured)
  - Social sentiment (Reddit/Twitter)
  - Insider sentiment
  - AI-analyzed sentiment scores

### News - Finnhub (4 tools)
- `search_news` - Search news by symbol or keyword
- `get_company_news` - Company-specific headlines
- `get_market_news` - General market news (forex, crypto, merger)
- `get_social_sentiment` - Reddit/Twitter sentiment metrics

### News - IB Native (3 tools)
- `get_ib_news_providers` - List available IB news sources (Reuters, Dow Jones, etc.)
- `get_ib_news` - Get historical news from IB for a symbol
- `get_ib_news_article` - Get full article text by article ID

### Sentiment (3 tools)
- `analyze_news_sentiment` - AI sentiment analysis on news
- `analyze_text_sentiment` - Sentiment analysis on custom text
- `get_insider_sentiment` - Insider trading signals

### Utility (1 tool)
- `check_connection_status` - Check IB and API connections

## Configuration

### Environment Variables (.env file)

| Variable | Default | Description |
|----------|---------|-------------|
| `IB_HOST` | 127.0.0.1 | IB Gateway/TWS host |
| `IB_PORT` | 4001 | API port (see port reference below) |
| `IB_CLIENT_ID` | 1 | Unique client identifier |
| `FINNHUB_API_KEY` | - | Required for news features |
| `SENTIMENT_MODEL` | vader | `vader` (fast) or `finbert` (accurate) |
| `NEWS_CACHE_TTL` | 300 | News cache validity in seconds |
| `SENTIMENT_CACHE_TTL` | 3600 | Sentiment cache validity in seconds |
| `LOG_LEVEL` | INFO | Logging level |

### IB Port Reference

| Port | Service | Mode |
|------|---------|------|
| 4001 | IB Gateway | Paper Trading (recommended) |
| 4002 | IB Gateway | Live Trading |
| 7497 | TWS | Paper Trading |
| 7496 | TWS | Live Trading |

## Quick Start

### Mac/Linux
```bash
./setup.sh
```

### Windows
```cmd
setup.bat
```

Both scripts will:
1. Check Python 3.10+ installation
2. Create virtual environment
3. Install dependencies
4. Walk through configuration
5. Test API connections
6. Provide Claude Desktop config

## Claude Desktop Integration

Add to your Claude Desktop config:

**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ib-portfolio": {
      "command": "/path/to/ib-mcp-server/.venv/bin/python",
      "args": ["-m", "ib_mcp.server"],
      "cwd": "/path/to/ib-mcp-server"
    }
  }
}
```

## External Services

### Interactive Brokers Gateway
- Download: https://www.interactivebrokers.com/en/trading/ibgateway-stable.php
- Requires IB account with API access enabled
- Must be running locally when using portfolio features
- Enable "Read-Only API" in settings for safety

### Finnhub API
- Sign up: https://finnhub.io/register
- Free tier: 60 requests/minute
- Required for Finnhub news and sentiment features

### IB News Providers
The server also supports IB's native news feeds, which may include premium sources based on your IB subscription:
- **BRFG** - Briefing.com
- **DJ-N** - Dow Jones News
- **DJ-RT** - Dow Jones Real-Time
- **RTRS** - Reuters News
- **BSW** - Benzinga

Use `get_ib_news_providers` to see which providers are available for your account.

## Common Claude Prompts

Once set up, try asking Claude:

**Portfolio:**
- "What's my portfolio value?"
- "Show me all my positions"
- "Show my P&L for today"

**Market Data:**
- "What's the current price of AAPL?"
- "Show me TSLA's price history for the last month"

**Comprehensive News (recommended):**
- "Give me a full news analysis for NVDA"
- "What's the complete sentiment picture for Tesla?"
- "Analyze all news and sentiment for Apple"

**Individual News Sources:**
- "Get me IB news for AAPL from the last 3 days"
- "What news providers are available from IB?"
- "Show me Finnhub news for Microsoft"
- "What's the Reddit sentiment on GME?"

## Architecture Notes

- **Async-first:** All I/O operations use async/await
- **Lazy initialization:** Clients connect on first use
- **Caching:** TTL-based caching reduces API calls
- **Error handling:** Helpful error messages with troubleshooting tips
- **Read-only:** No order placement capability by design

## Troubleshooting

### "Connection refused" error
- Ensure IB Gateway/TWS is running
- Check the port matches your IB Gateway settings
- Verify "Enable ActiveX and Socket Clients" is checked in IB Gateway

### "Invalid API key" error
- Verify your Finnhub API key in .env
- Check for extra spaces or quotes around the key

### Claude doesn't see the tools
- Restart Claude Desktop after updating config
- Verify paths in claude_desktop_config.json are absolute
- Check Claude Desktop logs for errors
