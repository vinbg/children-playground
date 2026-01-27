"""MCP Tool definitions for portfolio, market data, news, and sentiment."""

from .portfolio import portfolio_tools
from .market_data import market_data_tools
from .news import news_tools
from .sentiment import sentiment_tools
from .utilities import utility_tools

all_tools = [
    *portfolio_tools,
    *market_data_tools,
    *news_tools,
    *sentiment_tools,
    *utility_tools,
]

__all__ = [
    "all_tools",
    "portfolio_tools",
    "market_data_tools",
    "news_tools",
    "sentiment_tools",
    "utility_tools",
]
