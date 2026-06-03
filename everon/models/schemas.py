# models/schemas.py

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, validator


class ToolDefinition(BaseModel):
    """
    Represents a validated tool discovered via the Synapse Agent Protocol (SAP).
    """
    tool_id: str = Field(
        ..., 
        description="The unique identification string of the tool on the SAP network registry."
    )
    name: str = Field(
        ..., 
        description="The human-readable name of the tool capability."
    )
    description: str = Field(
        ..., 
        description="A brief functional summary outlining what tasks this tool can perform."
    )
    cost_per_execution: int = Field(
        ..., 
        ge=0,
        description="The execution fee required by the tool provider, denominated in lamports."
    )
    payment_type: str = Field(
        ..., 
        description="The required payment settlement rails. Allowed values: 'escrow' or 'x402'."
    )
    endpoint_url: str = Field(
        ..., 
        description="The fully qualified service URL where the payload must be routed."
    )

    @validator("payment_type")
    def validate_payment_type(cls, v: str) -> str:
        normalized = v.lower().strip()
        if normalized not in ["escrow", "x402"]:
            raise ValueError("payment_type must be either 'escrow' or 'x402'")
        return normalized

    class Config:
        frozen = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "tool_id": "ace-market-analyzer-v1",
                "name": "Ace Cloud Multi-API Scanner",
                "description": "Aggregated market pattern analyzer via Ace Data Cloud platform.",
                "cost_per_execution": 5000,
                "payment_type": "x402",
                "endpoint_url": "https://api.acedata.cloud/v1/analyze"
            }
        }


class MarketSignals(BaseModel):
    """
    Encapsulates raw data frames ingested from the 3 combined Ace Data Cloud service pipelines.
    """
    ticker: str = Field(
        ..., 
        description="The uppercase asset tracking ticker symbol (e.g., 'SOL', 'SUI')."
    )
    sentiment_score: float = Field(
        ..., 
        ge=-1.0, 
        le=1.0, 
        description="The computed social sentiment bias ranging strictly between -1.0 (bearish) and 1.0 (bullish)."
    )
    rsi: float = Field(
        ..., 
        ge=0.0, 
        le=100.0, 
        description="The mathematical Relative Strength Index oscillator boundary metric."
    )
    macd_signal: str = Field(
        ..., 
        description="The descriptive directional momentum indicator flag (e.g., 'BULLISH', 'BEARISH', 'NEUTRAL')."
    )
    patterns_detected: List[str] = Field(
        default_factory=list, 
        description="A list of structural chart formations identified by the pattern analyzer."
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="The exact ISO UTC datetime marker confirming signal ingestion."
    )

    @validator("ticker")
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper().strip()

    @validator("macd_signal")
    def uppercase_macd(cls, v: str) -> str:
        return v.upper().strip()

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class DecisionOutput(BaseModel):
    """
    The definitive strategy commitment object computed by the autonomous system's internal scoring engine.
    """
    ticker: str = Field(
        ..., 
        description="The uppercase asset tracking ticker symbol targeted during the current sequence."
    )
    action: str = Field(
        ..., 
        description="The designated strategic operational instruction. Allowed values: 'BUY', 'SELL', 'HOLD'."
    )
    confidence_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="The deterministic confidence value (0.0 to 1.0) derived from our internal execution weighting matrix."
    )
    justification: str = Field(
        ..., 
        description="A detailed human-readable breakdown explaining how the engine formulated its final action strategy."
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="The exact ISO UTC datetime marker mapping the decision point."
    )

    @validator("ticker")
    def uppercase_ticker(cls, v: str) -> str:
        return v.upper().strip()

    @validator("action")
    def validate_action(cls, v: str) -> str:
        normalized = v.upper().strip()
        if normalized not in ["BUY", "SELL", "HOLD"]:
            raise ValueError("action must be one of 'BUY', 'SELL', or 'HOLD'")
        return normalized

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
