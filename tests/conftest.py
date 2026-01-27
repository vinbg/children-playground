"""Pytest fixtures for IB MCP Server tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ib_mcp.config import IBConfig, NewsConfig, SentimentConfig


@pytest.fixture
def ib_config():
    """Create test IB configuration."""
    return IBConfig(
        host="127.0.0.1",
        port=7497,
        client_id=999,
        timeout=10,
        readonly=True,
    )


@pytest.fixture
def news_config():
    """Create test news configuration."""
    return NewsConfig(
        finnhub_api_key="test_finnhub_key",
        alphavantage_api_key="test_av_key",
        cache_ttl=60,
    )


@pytest.fixture
def sentiment_config():
    """Create test sentiment configuration."""
    return SentimentConfig(
        model="vader",  # Use VADER for faster tests
        cache_ttl=60,
    )


@pytest.fixture
def mock_ib():
    """Create a mock IB client."""
    ib = MagicMock()
    ib.isConnected.return_value = True
    ib.managedAccounts.return_value = ["DU123456"]
    ib.positions.return_value = []
    ib.openOrders.return_value = []
    ib.connectAsync = AsyncMock()
    ib.accountSummaryAsync = AsyncMock(return_value=[])
    ib.accountValuesAsync = AsyncMock(return_value=[])
    ib.reqExecutionsAsync = AsyncMock(return_value=[])
    ib.qualifyContractsAsync = AsyncMock(return_value=[])
    ib.reqHistoricalDataAsync = AsyncMock(return_value=[])
    ib.reqContractDetailsAsync = AsyncMock(return_value=[])
    ib.reqMatchingSymbolsAsync = AsyncMock(return_value=[])
    return ib
