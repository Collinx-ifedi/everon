# payments/x402_client.py

from __future__ import annotations
import os
import sys
from pathlib import Path
import json
import base64
import logging
import uuid
from typing import Dict, Any, Optional

# AceDataCloud official Python SDK imports
try:
    from acedatacloud import AsyncAceDataCloud
    from acedatacloud_x402 import (
        create_x402_payment_handler,
        SolanaKeypairSigner,
        sign_solana_payment
    )
except ImportError as e:
    raise ImportError("Critical dependency missing. Please run: pip install acedatacloud acedatacloud-x402") from e

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from config import settings
from utils.file_manager import append_agent_log

logger = logging.getLogger("EveronAgent")


class X402PaymentClient:
    """
    Production-grade X402 payment protocol client.
    Handles cryptographic signing of SPL USDC transactions and manages the 
    AceDataCloud SDK lifecycle for pay-per-request infrastructure.
    """

    def __init__(self) -> None:
        self.agent_name = "Everon"
        
        # Securely unpack the SecretStr from Pydantic settings if it exists
        raw_key = getattr(settings, "SOLANA_PRIVATE_KEY", None)
        if raw_key and hasattr(raw_key, "get_secret_value"):
            self.private_key = raw_key.get_secret_value()
        else:
            self.private_key = raw_key
        
        if not self.private_key:
            logger.critical("SOLANA_PRIVATE_KEY is missing from configuration. X402 payments will fail.")
            self.signer = None
        else:
            try:
                self.signer = SolanaKeypairSigner.from_base58(self.private_key)
                logger.info("SolanaKeypairSigner successfully initialized for X402 client.")
            except Exception as e:
                logger.critical(f"Failed to load Solana keypair for X402 signer: {e}")
                self.signer = None

    async def get_managed_sdk_client(self) -> Optional[AsyncAceDataCloud]:
        """
        Instantiates the official AceDataCloud Async client equipped with the 
        X402 payment handler. Configured to default to the 'upto' scheme 
        for optimal metered billing on generative API routes.
        
        Returns:
            AsyncAceDataCloud: The managed client ready for API execution, or None if signer fails.
        """
        if not self.signer:
            await append_agent_log(f"[{self.agent_name}] X402 SDK initialization aborted: No valid signer.", level="ERROR")
            return None

        try:
            handler = create_x402_payment_handler(
                network="solana",
                solana_signer=self.signer,
                prefer_scheme="upto"  # Opt-in to ceiling-based metering
            )
            
            client = AsyncAceDataCloud(payment_handler=handler)
            return client
            
        except Exception as e:
            logger.error(f"Failed to build managed AsyncAceDataCloud client: {e}")
            await append_agent_log(f"[{self.agent_name}] X402 Payment Handler creation fault.", level="ERROR")
            return None

    async def generate_payment_header(self, requirement: Dict[str, Any]) -> Optional[str]:
        """
        Low-level envelope signing method. Takes an incoming 402 Payment Required 
        parameter block, normalizes structural mismatches, signs it via the Solana keypair, 
        and produces the Base64-encoded X-PAYMENT header string required by the RPC Server.
        """
        if not self.signer:
            logger.error("Cannot sign X402 payment envelope: Signer is offline.")
            return None

        if not requirement:
            logger.warning("Empty payment requirement passed to X402 signer.")
            return None

        await append_agent_log(f"[{self.agent_name}] Generating X402 cryptographic payment envelope...")

        # -------------------------------------------------------------------------
        # NORMALIZATION BLOCK
        # Extracts nested JSON layers and forces camelCase conformity for the SDK
        # -------------------------------------------------------------------------
        target_req = requirement
        
        # 0. Handle X402 v2 Multi-chain "accepts" array
        if "accepts" in target_req and isinstance(target_req["accepts"], list):
            # Scan array for the Solana specific requirement payload
            solana_req = next((req for req in target_req["accepts"] if req.get("network") == "solana"), None)
            if solana_req:
                target_req = solana_req
            else:
                logger.error("No 'solana' network option found in X402 v2 'accepts' array.")
                return None
        # 1. Fallback: Un-nest the requirements if the API wrapped them (X402 v1)
        elif "requirements" in target_req:
            target_req = target_req["requirements"]
        elif "error" in target_req and isinstance(target_req["error"], dict) and "requirements" in target_req["error"]:
            target_req = target_req["error"]["requirements"]

        normalized_req = dict(target_req)

        # 2. Map 'payTo' (Handle snake_case or alternative naming)
        if "payTo" not in normalized_req:
            normalized_req["payTo"] = normalized_req.get("pay_to") or normalized_req.get("wallet") or normalized_req.get("provider_wallet")

        # 3. Map 'amount' (In X402 v2, the target ceiling is often mapped as 'maxAmountRequired')
        if "amount" not in normalized_req:
            normalized_req["amount"] = normalized_req.get("maxAmountRequired") or normalized_req.get("cost") or normalized_req.get("price") or normalized_req.get("lamports")

        # 4. Map 'nonce'
        if "nonce" not in normalized_req:
            normalized_req["nonce"] = normalized_req.get("id") or normalized_req.get("request_id") or str(uuid.uuid4())

        # Abort if we still can't find a valid destination address
        if not normalized_req.get("payTo"):
            logger.error(f"X402 payload is missing a destination address ('payTo') after normalization. Raw: {requirement}")
            return None
        # -------------------------------------------------------------------------

        try:
            # Produce the signature dictionary from the sanitized target requirement
            envelope = sign_solana_payment(normalized_req, self.signer)
            
            # Stringify the JSON structure with zero whitespace to ensure hash integrity
            json_str = json.dumps(envelope, separators=(',', ':'))
            
            # Base64-encode the payload to build the HTTP header value
            x_payment_header_value = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
            
            await append_agent_log(f"[{self.agent_name}] X402 payment envelope successfully signed and encoded.")
            return x_payment_header_value
            
        except Exception as e:
            logger.error(f"Cryptographic signing failure during X402 envelope generation: {e}", exc_info=True)
            await append_agent_log(f"[{self.agent_name}] Fatal error signing X402 transaction payload.", level="ERROR")
            return None
