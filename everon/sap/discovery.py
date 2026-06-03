# sap/discovery.py

from __future__ import annotations
import sys
import os
from pathlib import Path
import logging
from typing import List, Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from sap.client import SynapseSAPClient
from models.schemas import ToolDefinition
from utils.file_manager import append_agent_log

logger = logging.getLogger("EveronAgent")


class SynapseToolDiscoveryEngine:
    """
    Production-level discovery pipeline tasked with finding available microservice
    capabilities across the Synapse network and verifying structural security compliance
    via the Synapse Sentinel verification contract.
    """

    def __init__(self, client: Optional[SynapseSAPClient] = None) -> None:
        self.agent_name = "Everon"
        # Re-use existing client instantiation or spin up a dedicated instance
        self.client = client or SynapseSAPClient()
        self.sentinel_address = "Ccr2yK3hLALU4p8oNRqrh4dGuvPJTth5KCLMio8cE1ph"

    async def discover_tools_by_capability(self, capability: str) -> List[ToolDefinition]:
        """
        Queries the SAP gateway to discover tools exposing a given capability.
        Converts raw JSON responses into validated Pydantic model configurations.

        Args:
            capability: Functional taxonomy tag (e.g., 'market_intelligence', 'execution')
            
        Returns:
            List[ToolDefinition]: Array of validated, schema-compliant tool records.
        """
        method = "sap_discoverTools"
        params = {"capability": capability.strip().lower()}

        await append_agent_log(f"[{self.agent_name}] Querying network registry for capability: '{capability}'")
        
        rpc_result = await self.client.send_rpc_request(method, params)
        
        if not rpc_result or "tools" not in rpc_result:
            await append_agent_log(f"[{self.agent_name}] No matching tools discovered for capability '{capability}'.", level="WARNING")
            return []

        validated_tools: List[ToolDefinition] = []
        raw_tools = rpc_result.get("tools", [])

        for idx, tool_data in enumerate(raw_tools):
            try:
                # Direct validation instantiation enforcing Pydantic models compiled in schemas.py
                tool_def = ToolDefinition(
                    tool_id=tool_data.get("tool_id"),
                    name=tool_data.get("name"),
                    description=tool_data.get("description"),
                    cost_per_execution=int(tool_data.get("cost_per_execution", 0)),
                    payment_type=tool_data.get("payment_type"),
                    endpoint_url=tool_data.get("endpoint_url")
                )
                validated_tools.append(tool_def)
            except Exception as schema_err:
                # Fault isolation: Skip malformed tool nodes to avoid stopping discovery execution loops
                logger.error(f"Structural validation skipped for discovered tool block index {idx}: {schema_err}")
                continue

        await append_agent_log(f"[{self.agent_name}] Discovered and validated {len(validated_tools)} tools for capability '{capability}'.")
        return validated_tools

    async def verify_tool_with_sentinel(self, tool_id: str) -> bool:
        """
        Submits a target tool registration reference to the Synapse Sentinel verification
        route to confirm cryptographic signature validation and payload protection.

        Args:
            tool_id: Unique identification string of the registered tool capability.

        Returns:
            bool: True if fully verified by the Sentinel, False otherwise.
        """
        method = "sap_verifyWithSentinel"
        params = {
            "tool_id": tool_id,
            "sentinel_address": self.sentinel_address
        }

        await append_agent_log(f"[{self.agent_name}] Initiating Sentinel security scan for tool target: '{tool_id}'")

        rpc_result = await self.client.send_rpc_request(method, params)
        
        if not rpc_result:
            await append_agent_log(f"[{self.agent_name}] Sentinel node verification handshake timed out or rejected request.", level="ERROR")
            return False

        # Evaluate explicitly typed status codes returned from the RPC signature validation
        verification_status = str(rpc_result.get("status", "")).strip().lower()
        cryptographic_signature = rpc_result.get("signature")

        if verification_status == "verified" and cryptographic_signature:
            await append_agent_log(f"[{self.agent_name}] Security Clearance Granted for '{tool_id}' via Sentinel contract verification.")
            return True
        
        logger.warning(f"Sentinel verification rejected tool '{tool_id}'. Status: {verification_status}")
        await append_agent_log(f"[{self.agent_name}] SECURITY ALERT: Sentinel verification failed for '{tool_id}'!", level="WARNING")
        return False

    async def get_trusted_execution_tool(self, capability: str) -> Optional[ToolDefinition]:
        """
        High-level pipeline wrapper combining lookup and verification steps.
        Finds tools matching a capability and outputs the first tool that clears
        the Synapse Sentinel safety threshold.
        """
        discovered_tools = await self.discover_tools_by_capability(capability)
        
        for tool in discovered_tools:
            is_secure = await self.verify_tool_with_sentinel(tool.tool_id)
            if is_secure:
                return tool
                
        return None