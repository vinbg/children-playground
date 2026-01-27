"""Main MCP Server for Interactive Brokers Portfolio Tracking."""

import asyncio
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .config import get_config
from .clients.ib_client import IBClient
from .clients.news_client import NewsClient
from .clients.sentiment import SentimentAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ib-mcp-server")

# Initialize server
server = Server("ib-mcp-server")

# Lazy-initialized clients
_ib_client: IBClient | None = None
_news_client: NewsClient | None = None
_sentiment_analyzer: SentimentAnalyzer | None = None


def get_ib_client() -> IBClient:
    """Get or create IB client instance."""
    global _ib_client
    if _ib_client is None:
        config = get_config()
        _ib_client = IBClient(config.ib)
    return _ib_client


def get_news_client() -> NewsClient:
    """Get or create news client instance."""
    global _news_client
    if _news_client is None:
        config = get_config()
        _news_client = NewsClient(config.news)
    return _news_client


def get_sentiment_analyzer() -> SentimentAnalyzer:
    """Get or create sentiment analyzer instance."""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        config = get_config()
        _sentiment_analyzer = SentimentAnalyzer(config.sentiment)
    return _sentiment_analyzer


# =============================================================================
# Tool Definitions
# =============================================================================

TOOLS = [
    # Portfolio Tools
    Tool(
        name="get_account_summary",
        description="Get account summary including net liquidation value, buying power, cash balance, and margin info.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account ID (optional, uses default if not provided)"
                }
            },
            "required": []
        }
    ),
    Tool(
        name="get_positions",
        description="Get all current positions with quantities, average cost, market value, and unrealized P&L.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account ID (optional)"
                },
                "include_zero": {
                    "type": "boolean",
                    "description": "Include zero positions",
                    "default": False
                }
            },
            "required": []
        }
    ),
    Tool(
        name="get_portfolio_pnl",
        description="Get detailed P&L breakdown - daily, unrealized, and realized gains/losses.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account ID (optional)"
                }
            },
            "required": []
        }
    ),
    Tool(
        name="get_position_details",
        description="Get detailed info for a specific position including cost basis, quantity, and P&L.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock/ETF symbol (e.g., AAPL, SPY)"
                },
                "account_id": {
                    "type": "string",
                    "description": "Account ID (optional)"
                }
            },
            "required": ["symbol"]
        }
    ),
    Tool(
        name="get_open_orders",
        description="List all open/pending orders in the account.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account ID (optional)"
                }
            },
            "required": []
        }
    ),
    Tool(
        name="get_executions",
        description="Get recent trade executions/fills.",
        inputSchema={
            "type": "object",
            "properties": {
                "days_back": {
                    "type": "integer",
                    "description": "Number of days to look back",
                    "default": 1
                },
                "symbol": {
                    "type": "string",
                    "description": "Filter by symbol (optional)"
                }
            },
            "required": []
        }
    ),
    # Market Data Tools
    Tool(
        name="get_quote",
        description="Get real-time or delayed quote for a symbol including bid, ask, last price, and volume.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock/ETF symbol"
                },
                "include_extended": {
                    "type": "boolean",
                    "description": "Include extended hours data",
                    "default": False
                }
            },
            "required": ["symbol"]
        }
    ),
    Tool(
        name="get_historical_data",
        description="Get historical OHLCV data for a symbol.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock/ETF symbol"
                },
                "duration": {
                    "type": "string",
                    "description": "Duration (e.g., '1 D', '1 W', '1 M', '1 Y')",
                    "default": "1 M"
                },
                "bar_size": {
                    "type": "string",
                    "description": "Bar size (e.g., '1 day', '1 hour', '5 mins')",
                    "default": "1 day"
                }
            },
            "required": ["symbol"]
        }
    ),
    Tool(
        name="get_contract_details",
        description="Get detailed contract information for a symbol including exchange, currency, and trading hours.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock/ETF symbol"
                }
            },
            "required": ["symbol"]
        }
    ),
    Tool(
        name="search_symbols",
        description="Search for contract symbols by name or partial match.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query"
                },
                "security_type": {
                    "type": "string",
                    "description": "Security type: STK, OPT, FUT, etc.",
                    "default": "STK"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    ),
    # News Tools
    Tool(
        name="search_news",
        description="Search financial news by symbol or keyword using Finnhub/Alpha Vantage.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol to search news for (optional)"
                },
                "keywords": {
                    "type": "string",
                    "description": "Search keywords (optional)"
                },
                "category": {
                    "type": "string",
                    "description": "News category: general, forex, crypto, merger",
                    "default": "general"
                },
                "from_date": {
                    "type": "string",
                    "description": "Start date YYYY-MM-DD (optional)"
                },
                "to_date": {
                    "type": "string",
                    "description": "End date YYYY-MM-DD (optional)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results",
                    "default": 10
                }
            },
            "required": []
        }
    ),
    Tool(
        name="get_company_news",
        description="Get latest news specifically for a company/symbol.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results",
                    "default": 10
                }
            },
            "required": ["symbol"]
        }
    ),
    Tool(
        name="get_market_news",
        description="Get general market news and headlines.",
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Category: general, forex, crypto, merger",
                    "default": "general"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results",
                    "default": 10
                }
            },
            "required": []
        }
    ),
    # Sentiment Tools
    Tool(
        name="analyze_news_sentiment",
        description="Analyze sentiment of news articles for a symbol using FinBERT.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol"
                },
                "days_back": {
                    "type": "integer",
                    "description": "Days of news to analyze",
                    "default": 7
                }
            },
            "required": ["symbol"]
        }
    ),
    Tool(
        name="get_social_sentiment",
        description="Get social media sentiment metrics from Finnhub.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol"
                }
            },
            "required": ["symbol"]
        }
    ),
    Tool(
        name="analyze_text_sentiment",
        description="Analyze sentiment of custom text using financial sentiment models.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to analyze"
                }
            },
            "required": ["text"]
        }
    ),
    Tool(
        name="get_insider_sentiment",
        description="Get insider trading sentiment and transactions.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol"
                }
            },
            "required": ["symbol"]
        }
    ),
    # Utility Tools
    Tool(
        name="check_connection_status",
        description="Check connection status to IB Gateway/TWS and news APIs.",
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    logger.info(f"Tool called: {name} with args: {arguments}")

    try:
        result = await handle_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        error_result = {
            "error": type(e).__name__,
            "message": str(e),
        }
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]


async def handle_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Route tool calls to appropriate handlers."""

    # Portfolio Tools
    if name == "get_account_summary":
        return await get_ib_client().get_account_summary(args.get("account_id"))

    elif name == "get_positions":
        return await get_ib_client().get_positions(
            account_id=args.get("account_id"),
            include_zero=args.get("include_zero", False)
        )

    elif name == "get_portfolio_pnl":
        return await get_ib_client().get_portfolio_pnl(args.get("account_id"))

    elif name == "get_position_details":
        return await get_ib_client().get_position_details(
            symbol=args["symbol"],
            account_id=args.get("account_id")
        )

    elif name == "get_open_orders":
        return await get_ib_client().get_open_orders(args.get("account_id"))

    elif name == "get_executions":
        return await get_ib_client().get_executions(
            days_back=args.get("days_back", 1),
            symbol=args.get("symbol")
        )

    # Market Data Tools
    elif name == "get_quote":
        return await get_ib_client().get_quote(
            symbol=args["symbol"],
            include_extended=args.get("include_extended", False)
        )

    elif name == "get_historical_data":
        return await get_ib_client().get_historical_data(
            symbol=args["symbol"],
            duration=args.get("duration", "1 M"),
            bar_size=args.get("bar_size", "1 day")
        )

    elif name == "get_contract_details":
        return await get_ib_client().get_contract_details(args["symbol"])

    elif name == "search_symbols":
        return await get_ib_client().search_symbols(
            query=args["query"],
            security_type=args.get("security_type", "STK"),
            limit=args.get("limit", 10)
        )

    # News Tools
    elif name == "search_news":
        return await get_news_client().search_news(
            symbol=args.get("symbol"),
            keywords=args.get("keywords"),
            category=args.get("category", "general"),
            from_date=args.get("from_date"),
            to_date=args.get("to_date"),
            limit=args.get("limit", 10)
        )

    elif name == "get_company_news":
        return await get_news_client().get_company_news(
            symbol=args["symbol"],
            limit=args.get("limit", 10)
        )

    elif name == "get_market_news":
        return await get_news_client().get_market_news(
            category=args.get("category", "general"),
            limit=args.get("limit", 10)
        )

    # Sentiment Tools
    elif name == "analyze_news_sentiment":
        news = await get_news_client().get_company_news(
            symbol=args["symbol"],
            limit=20
        )
        return await get_sentiment_analyzer().analyze_news_sentiment(
            news_items=news.get("articles", []),
            symbol=args["symbol"]
        )

    elif name == "get_social_sentiment":
        return await get_news_client().get_social_sentiment(args["symbol"])

    elif name == "analyze_text_sentiment":
        return await get_sentiment_analyzer().analyze_text(args["text"])

    elif name == "get_insider_sentiment":
        return await get_news_client().get_insider_sentiment(args["symbol"])

    # Utility Tools
    elif name == "check_connection_status":
        ib_status = await get_ib_client().check_connection()
        news_status = get_news_client().check_api_keys()
        return {
            "ib_connection": ib_status,
            "news_apis": news_status,
            "sentiment_model": get_config().sentiment.model,
        }

    else:
        raise ValueError(f"Unknown tool: {name}")


async def run_server():
    """Run the MCP server."""
    config = get_config()
    logging.getLogger().setLevel(config.log_level)

    logger.info("Starting IB MCP Server...")
    logger.info(f"IB Gateway: {config.ib.host}:{config.ib.port}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """Entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
