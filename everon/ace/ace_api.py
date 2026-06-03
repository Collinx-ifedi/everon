# ace/ace_api.py

from __future__ import annotations
import os
import sys
from pathlib import Path
import logging
import json
from typing import Dict, Any, List
import httpx
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from config import settings
from utils.file_manager import append_agent_log

# Production local module imports
from src.data.market_data import MarketDataFetcher
from src.analysis.technical_analysis import TechnicalAnalyzer
from src.sentiment.sentiment_utils import hybrid_sentiment

logger = logging.getLogger("Everon")


class AceDataCloudInterface:
    """
    Unified production-level orchestrator interface connecting local analytical engines 
    with the explicit, specialized endpoints of Ace Data Cloud across 10 target assets.
    """

    def __init__(self) -> None:
        self.api_key = settings.ACE_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        # Explicitly targeted 10-coin system asset matrix
        self.target_tokens = [
            "SOL", "BTC", "ETH", "HYPE", "BONK", 
            "PUMP", "JUP", "HELIUM", "XRP", "HBAR"
        ]

    async def fetch_market_news(self, token: str) -> List[Dict[str, Any]]:
        """
        SERVICE 1: Google SERP Service (Ace Data Cloud)
        Pipes query requests directly to the standalone Google SERP endpoint.
        Endpoint: https://api.acedata.cloud/serp/google
        """
        url = "https://api.acedata.cloud/serp/google"
        query_string = f"{token} crypto cryptocurrency token financial market news updates"
        
        payload = {
            "q": query_string
        }

        await append_agent_log(f"Invoking Ace Google SERP API for token: {token}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("organic_results", [])
                    if not results and "news_results" in data:
                        results = data.get("news_results", [])
                    
                    await append_agent_log(f"Successfully retrieved {len(results)} search updates from SERP Service.")
                    return results
                
                logger.error(f"Ace SERP Service returned non-200 state [{response.status_code}]: {response.text}")
                return []
            except Exception as e:
                logger.error(f"Unexpected network or response crash in SERP Service engine loop: {e}")
                return []

    async def analyze_sentiment_gemini(self, news_articles: List[Dict[str, Any]]) -> float:
        """
        SERVICE 2: Gemini LLM Service (Ace Data Cloud)
        Feeds text fragments through the local `hybrid_sentiment` parser before 
        routing payload properties to the dedicated Gemini chat completions endpoint.
        Endpoint: https://api.acedata.cloud/gemini/chat/completions
        """
        url = "https://api.acedata.cloud/gemini/chat/completions"
        
        # Build text string frames from the real-time Google search summaries
        raw_text_corpus = " ".join([
            f"{art.get('title', '')} {art.get('snippet', '')}" 
            for art in news_articles[:5]
        ]).strip()

        if not raw_text_corpus:
            await append_agent_log("No active search summary updates found. Defaulting to neutral baseline.")
            return 0.0

        # Execute local heuristic sentiment engine
        try:
            local_sentiment = hybrid_sentiment(raw_text_corpus)
            local_score = local_sentiment.get("score", 0.0)
            local_cat = local_sentiment.get("category", "neutral")
        except Exception as local_err:
            logger.error(f"Local sentiment_utils execution failed: {local_err}")
            local_score = 0.0
            local_cat = "neutral"

        # Construct payload utilizing output parameters generated from sentiment_utils.py
        prompt = (
            "You are a specialized financial sentiment analysis agent.\n"
            "Evaluate the market data corpus and its matching pre-calculated sentiment telemetry values.\n"
            "You must return a raw JSON object string mapping an aggregated confidence sentiment score index:\n"
            '{"sentiment_score": <float between -1.0 and 1.0>}\n'
            "Do not output markdown block markers or conversational elements.\n\n"
            f"Pre-calculated Heuristic Score: {local_score}\n"
            f"Pre-calculated Heuristic Category: {local_cat}\n"
            f"Context Data Corpus:\n{raw_text_corpus}"
        )

        payload = {
            "model": "gemini-pro",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1
        }

        await append_agent_log("Routing processed sentiment frames to Ace Gemini completions endpoint...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"].strip()
                    
                    # Clean markdown wrappers if returned by the LLM
                    if content.startswith("```json"):
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif content.startswith("```"):
                        content = content.split("```")[1].split("```")[0].strip()
                        
                    parsed = json.loads(content)
                    return float(parsed.get("sentiment_score", local_score))
                
                logger.error(f"Ace Gemini Service returned error state [{response.status_code}]: {response.text}")
                return local_score
            except Exception as e:
                logger.error(f"Failed parsing Gemini structural payload. Dropping back to local baseline: {e}")
                return local_score

    async def evaluate_intelligence_gpt(
        self, 
        token: str, 
        sentiment_score: float, 
        tech_indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        SERVICE 3: OpenAI GPT LLM Service (Ace Data Cloud)
        Assembles all generated data metrics from local subfolder scripts into a composite 
        telemetry model and passes it to the dedicated OpenAI chat completions path.
        Endpoint: https://api.acedata.cloud/openai/chat/completions
        """
        url = "https://api.acedata.cloud/openai/chat/completions"

        # Build highly descriptive intelligence input frame combining all analytical components
        composite_telemetry = {
            "token": token,
            "refined_sentiment_index": sentiment_score,
            "technical_indicators_matrix": tech_indicators
        }

        prompt = (
            f"You are the Core Market Intelligence Engine for an autonomous agent tracking {token}.\n"
            "Process the provided input model payload comprising consolidated technical indicators, "
            "candle formation metrics, and refined financial sentiment scores.\n"
            "Formulate an actionable market intelligence overview. Output raw JSON matching this layout exactly:\n"
            '{"rsi": <float 0-100>, "macd_signal": "BULLISH"|"BEARISH"|"NEUTRAL", "patterns": ["Pattern1", "Pattern2"]}\n'
            f"Do not return markdown wrappers or trailing texts.\n\n"
            f"Input Telemetry Model:\n{json.dumps(composite_telemetry, indent=2)}"
        )

        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        await append_agent_log(f"Routing composite analytics to Ace GPT for Market Intelligence matrix resolution...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"].strip()
                    parsed = json.loads(content)
                    await append_agent_log(f"Market Intelligence matrix successfully synthesized via GPT for {token}.")
                    return parsed
                
                logger.error(f"Ace OpenAI Service returned error state [{response.status_code}]: {response.text}")
                return {"rsi": 50.0, "macd_signal": "NEUTRAL", "patterns": []}
            except Exception as e:
                logger.error(f"Failed to fetch market metrics from GPT pipeline network boundary: {e}")
                return {"rsi": 50.0, "macd_signal": "NEUTRAL", "patterns": []}

    async def fetch_all_signals(self, token: str) -> Dict[str, Any]:
        """
        Main orchestration entry point loops. Connects standard synchronous data engines 
        with asynchronous remote services to cleanly output unified trading signals.
        """
        # Step 1: Execute Service 1 - Scp news documents via Google Search endpoint
        articles = await self.fetch_market_news(token)
        
        # Step 2: Execute Service 2 - Evaluate refined scores via Gemini endpoint
        sentiment_score = await self.analyze_sentiment_gemini(articles)
        
        # Step 3: Fetch OHLCV data using synchronous MarketDataFetcher module
        try:
            fetcher = MarketDataFetcher(timeframe="1h", limit=100)
            df_ohlcv = fetcher.fetch_ohlcv(token)
        except Exception as market_err:
            logger.error(f"Synchronous MarketDataFetcher failed for asset {token}: {market_err}")
            df_ohlcv = None

        # Step 4: Map DataFrame rows into TechnicalAnalyzer to compile indicator objects
        tech_indicators = {}
        if df_ohlcv is not None and isinstance(df_ohlcv, pd.DataFrame) and not df_ohlcv.empty:
            try:
                analyzer = TechnicalAnalyzer(df_ohlcv)
                analyzer.generate_all_indicators()
                tech_indicators = analyzer.get_structured_summary()
            except Exception as tech_err:
                logger.error(f"TechnicalAnalyzer processing phase error: {tech_err}")
        else:
            await append_agent_log(f"No pricing charts available for token {token}. Using minimal telemetry.", level="WARNING")

        # Step 5: Execute Service 3 - Core Market Intelligence synthesis via GPT endpoint
        intelligence = await self.evaluate_intelligence_gpt(
            token=token,
            sentiment_score=sentiment_score,
            tech_indicators=tech_indicators
        )
        
        return {
            "ticker": token,
            "sentiment_score": sentiment_score,
            "rsi": float(intelligence.get("rsi", 50.0)),
            "macd_signal": str(intelligence.get("macd_signal", "NEUTRAL")),
            "patterns_detected": list(intelligence.get("patterns", []))
        }
