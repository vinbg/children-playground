"""Configuration management for IB MCP Server."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class IBConfig:
    """Interactive Brokers connection configuration."""

    host: str = "127.0.0.1"
    port: int = 4001  # Default to IB Gateway paper trading
    client_id: int = 1
    timeout: int = 30
    readonly: bool = True


@dataclass
class Config:
    """Main configuration class."""

    ib: IBConfig = field(default_factory=IBConfig)
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env_file: str | Path | None = None) -> "Config":
        """Load configuration from environment variables."""
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        ib_config = IBConfig(
            host=os.getenv("IB_HOST", "127.0.0.1"),
            port=int(os.getenv("IB_PORT", "4001")),
            client_id=int(os.getenv("IB_CLIENT_ID", "1")),
            timeout=int(os.getenv("IB_TIMEOUT", "30")),
            readonly=os.getenv("IB_READONLY", "true").lower() == "true",
        )

        return cls(
            ib=ib_config,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def reload_config() -> Config:
    """Reload configuration from environment."""
    global _config
    _config = Config.from_env()
    return _config
