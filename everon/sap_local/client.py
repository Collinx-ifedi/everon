# sap/client.py

from __future__ import annotations
import sys
import os
from pathlib import Path
import logging
import uuid
import httpx
from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from config import settings
from utils.file_manager import append_agent_log

# Initialize the primary logger using the specific agent identity
logger = logging.getLogger("EveronAgent")


class SynapseSAPClient:
    """
    Production-grade JSON-RPC 2.0 client for the Synapse Agent Protocol (SAP).
    Handles secure communication, payload formatting, and error boundary isolation 
    with the OOBE Protocol RPC Gateway.
    """

    def __init__(self) -> None:
        self.agent_name = "Everon"
        self.rpc_url = self._build_rpc_url()
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _build_rpc_url(self) -> str:
        """
        Ensures the API key is correctly appended to the RPC URL query parameters,
        handling both raw endpoint injection and isolated environment variables.
        """
        base_url = settings.SYNAPSE_RPC_URL
        
        parsed_url = urlparse(base_url)
        query_params = parse_qs(parsed_url.query)
        
        # If api_key is missing from the URL but exists in settings, append it
        if "api_key" not in query_params and hasattr(settings, "SYNAPSE_API_KEY") and settings.SYNAPSE_API_KEY:
            query_params["api_key"] = [settings.SYNAPSE_API_KEY]
            new_query = urlencode(query_params, doseq=True)
            parsed_url = parsed_url._replace(query=new_query)
            return urlunparse(parsed_url)
            
        return base_url

    async def send_rpc_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a strictly compliant JSON-RPC 2.0 payload against the Synapse Gateway.
        
        Args:
            method: The exact RPC command string (e.g., 'sap_discoverTools')
            params: The operational parameter matrix required by the endpoint.
            
        Returns:
            Dict[str, Any]: The parsed result object, or an empty dict if the request failed.
        """
        if params is None:
            params = {}

        # Generate a unique cryptographic request ID for transaction tracing
        request_id = str(uuid.uuid4())

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }

        await append_agent_log(f"[{self.agent_name}] Dispatching SAP RPC Call: {method} (Trace ID: {request_id[:8]})")

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                response = await client.post(self.rpc_url, json=payload, headers=self.headers)
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # Intercept JSON-RPC specific application error layers
                    if "error" in response_data:
                        error_payload = response_data["error"]
                        error_msg = error_payload.get('message', 'Unknown Error')
                        logger.error(f"SAP RPC Application Error [{method}]: {error_payload}")
                        await append_agent_log(f"RPC Application Error [{method}]: {error_msg}", level="ERROR")
                        return {}
                        
                    # Return the clean result structure object directly
                    return response_data.get("result", {})
                
                # Intercept infrastructure-level HTTP errors (e.g., 401 Unauthorized, 502 Bad Gateway)
                logger.error(f"SAP RPC HTTP Error [{response.status_code}]: {response.text}")
                await append_agent_log(f"HTTP Infrastructure Error {response.status_code} during {method}", level="ERROR")
                return {}

            except httpx.RequestError as exc:
                logger.error(f"Network transport disconnect during SAP RPC call '{method}': {exc}")
                await append_agent_log(f"Network transport failure executing {method}", level="ERROR")
                return {}
            except Exception as e:
                logger.error(f"Unexpected execution fault during SAP RPC call '{method}': {e}", exc_info=True)
                return {}