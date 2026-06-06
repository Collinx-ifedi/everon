# config.py

from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env (local development)
load_dotenv()


class ConfigError(Exception):
    """Raised when required configuration is missing."""


def get_env(
    key: str,
    default: str | None = None,
    required: bool = False,
) -> str:
    """
    Read an environment variable with validation.

    Args:
        key: Environment variable name.
        default: Default value if missing.
        required: Whether the variable is mandatory.

    Returns:
        str: Environment variable value.

    Raises:
        ConfigError: If a required variable is missing.
    """
    value = os.getenv(key, default)

    if required and not value:
        raise ConfigError(
            f"Missing required environment variable: {key}"
        )

    return value


@dataclass(frozen=True)
class Settings:
    """
    Application settings.
    """

    # =========================
    # Environment
    # =========================
    ENVIRONMENT: str
    DEBUG: bool

    # =========================
    # Synapse / SAP
    # =========================
    SYNAPSE_API_KEY: str
    SYNAPSE_RPC_URL: str

    # =========================
    # Ace Data Cloud
    # =========================
    ACE_API_KEY: str

    # =========================
    # Wallet & Cryptography
    # =========================
    SOLANA_WALLET_ADDRESS: str
    SOLANA_PRIVATE_KEY: str

    # =========================
    # Agent Runtime
    # =========================
    AGENT_NAME: str
    ANALYSIS_INTERVAL_SECONDS: int
    DATA_DIR: str

    # =========================
    # Logging
    # =========================
    LOG_LEVEL: str

    @classmethod
    def load(cls) -> "Settings":
        return cls(
            ENVIRONMENT=get_env(
                "ENVIRONMENT",
                default="development"
            ),

            DEBUG=get_env(
                "DEBUG",
                default="false"
            ).lower() == "true",

            SYNAPSE_API_KEY=get_env(
                "SYNAPSE_API_KEY",
                required=True
            ),

            SYNAPSE_RPC_URL=get_env(
                "SYNAPSE_RPC_URL",
                required=True
            ),

            ACE_API_KEY=get_env(
                "ACE_API_KEY",
                required=True
            ),

            SOLANA_WALLET_ADDRESS=get_env(
                "SOLANA_WALLET_ADDRESS",
                required=True
            ),
            
            SOLANA_PRIVATE_KEY=get_env(
                "SOLANA_PRIVATE_KEY",
                required=True
            ),

            AGENT_NAME=get_env(
                "AGENT_NAME",
                default="Solana Intelligence Agent"
            ),

            ANALYSIS_INTERVAL_SECONDS=int(
                get_env(
                    "ANALYSIS_INTERVAL_SECONDS",
                    default="900"
                )
            ),
            
            DATA_DIR=get_env(
                "DATA_DIR",
                default="data"
            ),

            LOG_LEVEL=get_env(
                "LOG_LEVEL",
                default="INFO"
            ).upper(),
        )


# Singleton settings object
settings = Settings.load()
