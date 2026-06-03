# payments/payment_manager.py

from __future__ import annotations
import os
import sys
from pathlib import Path
import logging
from typing import Dict, Any, Optional
import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from config import settings
from sap.client import SynapseSAPClient
from payment.x402_client import X402PaymentClient
from models.schemas import ToolDefinition
from utils.file_manager import append_agent_log

logger = logging.getLogger("EveronAgent")


class PaymentManager:
    """
    Unified Settlement Coordinator for the Everon agent.
    Dynamically routes tool execution requests through either on-chain OOBE Escrow 
    contracts or direct X402 streaming based on the verified ToolDefinition.
    """

    def __init__(self, sap_client: Optional[SynapseSAPClient] = None) -> None:
        self.agent_name = "Everon"
        # Inject existing client or create isolated instances
        self.sap_client = sap_client or SynapseSAPClient()
        self.x402_client = X402PaymentClient()

    async def execute_tool(self, tool: ToolDefinition, request_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Main orchestration router. Determines the settlement rail required by 
        the target tool and delegates execution to the appropriate payment pipeline.
        
        Args:
            tool: The verified schema representation of the target microservice.
            request_payload: The operational data to be processed by the tool.
            
        Returns:
            Optional[Dict[str, Any]]: The parsed JSON response from the tool, or None if failed.
        """
        await append_agent_log(f"[{self.agent_name}] Initiating execution sequence for tool '{tool.tool_id}' via {tool.payment_type.upper()} rails.")

        if tool.payment_type == "x402":
            return await self._execute_via_x402(tool, request_payload)
        elif tool.payment_type == "escrow":
            return await self._execute_via_escrow(tool, request_payload)
        else:
            logger.error(f"Unknown payment settlement rail requested: {tool.payment_type}")
            return None

    async def _execute_via_x402(self, tool: ToolDefinition, request_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Explicit execution pipeline for the X402 protocol.
        1. Submits initial request without payment headers.
        2. Intercepts the HTTP 402 Payment Required response.
        3. Signs the exact cryptographic requirement payload using X402PaymentClient.
        4. Injects the Base64 X-PAYMENT header and re-submits for settlement.
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Step 1: Initial standard request (Expected to fail with 402)
                await append_agent_log(f"[{self.agent_name}] Probing {tool.name} for X402 payment requirements...")
                probe_response = await client.post(tool.endpoint_url, json=request_payload, headers=headers)
                
                # If the endpoint doesn't require metering right now, accept the response
                if probe_response.status_code == 200:
                    return probe_response.json()
                    
                # Step 2: Intercept X402 Gateway Challenge
                if probe_response.status_code == 402:
                    requirement_payload = probe_response.json()
                    
                    # Step 3: Generate the signed payment header
                    x_payment_header = await self.x402_client.generate_payment_header(requirement_payload)
                    
                    if not x_payment_header:
                        logger.error("X402 Payment Handler failed to generate a valid cryptographic signature.")
                        return None
                        
                    # Step 4: Re-submit payload with explicit authentication header
                    headers["X-PAYMENT"] = x_payment_header
                    await append_agent_log(f"[{self.agent_name}] Transmitting signed X402 envelope to {tool.endpoint_url}...")
                    
                    settlement_response = await client.post(tool.endpoint_url, json=request_payload, headers=headers)
                    
                    if settlement_response.status_code == 200:
                        await append_agent_log(f"[{self.agent_name}] X402 Payment verified and request processed successfully.")
                        return settlement_response.json()
                    else:
                        logger.error(f"X402 settlement rejected [{settlement_response.status_code}]: {settlement_response.text}")
                        return None
                        
                # Handle unexpected infrastructure errors
                logger.error(f"X402 Target returned unexpected status [{probe_response.status_code}]: {probe_response.text}")
                return None

            except Exception as e:
                logger.error(f"Execution fault during X402 pipeline routing for {tool.tool_id}: {e}", exc_info=True)
                return None

    async def _execute_via_escrow(self, tool: ToolDefinition, request_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Explicit execution pipeline for OOBE Escrow protocol.
        1. Issues an RPC call to sap_settleEscrow against the Synapse Gateway.
        2. Confirms the transaction ledger update.
        3. Executes the API target after network validation clears.
        """
        wallet_address = getattr(settings, "SOLANA_WALLET_ADDRESS", None)
        
        if not wallet_address:
            logger.error("Cannot execute Escrow settlement: SOLANA_WALLET_ADDRESS is missing.")
            return None

        # Step 1: Formulate the strictly-typed JSON-RPC settlement instruction
        rpc_method = "sap_settleEscrow"
        rpc_params = {
            "agent_wallet": wallet_address,
            "tool_id": tool.tool_id,
            "calls_to_settle": 1,
            "cost_lamports": tool.cost_per_execution
        }

        await append_agent_log(f"[{self.agent_name}] Requesting OOBE Escrow ledger deduction for '{tool.tool_id}'...")
        
        # Step 2: Route transaction to the staging Synapse Gateway
        rpc_result = await self.sap_client.send_rpc_request(rpc_method, rpc_params)
        
        # Check explicit verification from the RPC gateway response
        settlement_status = str(rpc_result.get("status", "")).lower()
        if settlement_status not in ["success", "settled", "confirmed"]:
            logger.warning(f"Escrow settlement failed or was rejected by Synapse RPC: {rpc_result}")
            await append_agent_log(f"[{self.agent_name}] Insufficient Escrow balance or settlement rejected.", level="ERROR")
            return None
            
        await append_agent_log(f"[{self.agent_name}] Escrow settlement confirmed on-chain. Executing {tool.name}...")

        # Step 3: Execute the target tool logic post-settlement
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(tool.endpoint_url, json=request_payload, headers=headers)
                
                if response.status_code == 200:
                    return response.json()
                    
                logger.error(f"Target tool returned fault post-escrow settlement [{response.status_code}]: {response.text}")
                return None
                
            except Exception as e:
                logger.error(f"Network failure executing tool {tool.tool_id} post-settlement: {e}")
                return None
