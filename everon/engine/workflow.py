# workflow.py

from __future__ import annotations
import sys
import os
from pathlib import Path
import json
import logging
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from config import settings
from sap.registry import ToolRegistry
from payment.payment_manager import PaymentManager
from engine.decision_engine import EveronDecisionEngine
from models.schemas import ToolDefinition
from utils.file_manager import append_agent_log

logger = logging.getLogger("EveronAgent")


class EveronWorkflowProcessor:
    """
    Sequential Service Orchestrator for the Everon analytical loop.
    Discovers registry capabilities, negotiates payments via PaymentManager,
    synthesizes indicators via EveronDecisionEngine, and isolates failures
    gracefully to maintain persistent background execution across target tokens.
    """

    def __init__(self) -> None:
        self.agent_name = "Everon"
        
        # Initialize internal processing layers
        self.registry = ToolRegistry()
        self.payment_manager = PaymentManager()
        self.decision_engine = EveronDecisionEngine(x402_client=self.payment_manager.x402_client)
        
        # Output directory definition for tracking state preservation
        self.state_file_path = getattr(settings, "state_file_path", os.path.join("data", "market_intelligence.json"))
        os.makedirs("data", exist_ok=True)

    async def execute_full_market_scan(self, tracking_tokens: List[str]) -> Dict[str, Any]:
        """
        Runs a comprehensive analytical pass over the tracking index array.
        Isolates individual asset network anomalies to keep the overarching process active.
        
        Args:
            tracking_tokens: The list of ticker symbols (e.g., ['SOL', 'BTC', 'HYPE']).
            
        Returns:
            Dict[str, Any]: Collected and synthesized market intelligence state mapping.
        """
        await append_agent_log(f"[{self.agent_name}] Booting global market scan for index: {tracking_tokens}")
        
        global_synthesized_state: Dict[str, Any] = {}

        for token in tracking_tokens:
            try:
                await append_agent_log(f"[{self.agent_name}] Processing tracking routine for asset segment: {token}")
                
                # 1. Discover registered tools for Technical Analysis and Sentiment Analysis
                tech_tool: ToolDefinition = await self.registry.get_tool_by_capability(capability="technical_analysis", asset=token)
                sentiment_tool: ToolDefinition = await self.registry.get_tool_by_capability(capability="sentiment_analysis", asset=token)
                
                if not tech_tool or not sentiment_tool:
                    raise ValueError(f"Required data discovery tools missing for asset target: {token}")

                # 2. Execute Technical Analysis tool via the integrated payment manager routing layer
                tech_payload = {"token": token, "timeframe": "1h"}
                tech_response = await self.payment_manager.execute_tool(tech_tool, request_payload=tech_payload)
                
                if not tech_response:
                    raise ConnectionError(f"Technical Analysis endpoint failed to return valid response arrays for {token}")

                # 3. Execute Sentiment Analysis tool via payment manager
                sentiment_payload = {"query": token, "limit": 5}
                sentiment_response = await self.payment_manager.execute_tool(sentiment_tool, request_payload=sentiment_payload)
                
                if not sentiment_response:
                    raise ConnectionError(f"Social Sentiment endpoint dropped connection or failed verification for {token}")

                # 4. Feed analytical data arrays directly into the dual-model Decision Engine
                raw_tech_summary = tech_response.get("summary", {})
                raw_sentiment_items = sentiment_response.get("news_items", [])
                
                token_intelligence = await self.decision_engine.analyze_asset(
                    token=token, 
                    tech_summary=raw_tech_summary, 
                    sentiment_items=raw_sentiment_items
                )

                # 5. Append verified context block to the local runtime state tracker
                global_synthesized_state[token] = token_intelligence
                await append_agent_log(f"[{self.agent_name}] Intelligence synthesis for {token} completed successfully.")

            except Exception as e:
                # Intercept Sequence: Drop warning telemetric logs and isolate the coin completely
                warning_message = f"CRITICAL LOOP ANOMALY: Gracefully isolating asset symbol '{token}' due to pipeline processing failure: {e}"
                logger.warning(warning_message, exc_info=True)
                
                # Write error state directly to the local telemetric engine log
                await append_agent_log(f"[{self.agent_name}] ⚠️ {warning_message}", level="WARNING")
                
                # Structural fallback injection ensuring tracking metrics don't break downstream UI parsing
                global_synthesized_state[token] = {
                    "token": token,
                    "confidence_score": 0.0,
                    "directional_bias": "ERROR_ISOLATED",
                    "gemini_narrative": "Asset tracking temporarily halted. Connection or pipeline configuration timeout.",
                    "decision_status": "INDECISIVE",
                    "indecision_telemetry": {
                        "warning": "Everon isolated this token due to an unhandled system infrastructure fault.",
                        "reasons": [str(e)],
                        "strategic_advice": "Review system-wide provider status and network configurations."
                    }
                }
                # Continue loop directly to ensure remaining coins continue updating normally
                continue

        # 6. Preserve final synthesized state block to disk for the Streamlit tracking dashboard
        await self._preserve_synthesized_state(global_synthesized_state)
        return global_synthesized_state

    async def _preserve_synthesized_state(self, current_state: Dict[str, Any]) -> None:
        """
        Performs atomic state preservation to local storage. 
        Updates tracking matrices securely to prevent data corruption.
        """
        try:
            existing_state: Dict[str, Any] = {}
            
            # Read previous state if exists to perform seamless historical merge tracking
            if os.path.exists(self.state_file_path):
                try:
                    with open(self.state_file_path, "r", encoding="utf-8") as f:
                        existing_state = json.load(f)
                except Exception:
                    existing_state = {}

            # Update master keys cleanly
            existing_state.update(current_state)

            # Atomic save routine
            temp_path = f"{self.state_file_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(existing_state, f, indent=4, ensure_ascii=False)
                
            os.replace(temp_path, self.state_file_path)
            await append_agent_log(f"[{self.agent_name}] Final synthesized state flushed securely to {self.state_file_path}.")
            
        except Exception as e:
            logger.error(f"Failed to preserve agent structural state: {e}")
            await append_agent_log(f"[{self.agent_name}] Master state preservation failure.", level="ERROR")
