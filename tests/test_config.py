"""Tests for configuration management."""

import os
import pytest

from ib_mcp.config import Config, IBConfig, NewsConfig, SentimentConfig


def test_ib_config_defaults():
    """Test IBConfig default values."""
    config = IBConfig()
    assert config.host == "127.0.0.1"
    assert config.port == 4001
    assert config.client_id == 1
    assert config.readonly is True


def test_news_config_defaults():
    """Test NewsConfig default values."""
    config = NewsConfig()
    assert config.finnhub_api_key is None
    assert config.alphavantage_api_key is None
    assert config.cache_ttl == 300


def test_sentiment_config_defaults():
    """Test SentimentConfig default values."""
    config = SentimentConfig()
    assert config.model == "finbert"
    assert config.cache_ttl == 3600


def test_config_from_env(monkeypatch):
    """Test loading config from environment variables."""
    monkeypatch.setenv("IB_HOST", "192.168.1.100")
    monkeypatch.setenv("IB_PORT", "7496")
    monkeypatch.setenv("IB_CLIENT_ID", "5")
    monkeypatch.setenv("FINNHUB_API_KEY", "test_key")
    monkeypatch.setenv("SENTIMENT_MODEL", "vader")

    config = Config.from_env()

    assert config.ib.host == "192.168.1.100"
    assert config.ib.port == 7496
    assert config.ib.client_id == 5
    assert config.news.finnhub_api_key == "test_key"
    assert config.sentiment.model == "vader"
