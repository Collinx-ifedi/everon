# payments/x402_client.py

from __future__ import annotations
import os
import sys
from pathlib import Path
import json
import base64
import logging
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
        parameter block, signs it via the Solana keypair, and produces the exact 
        Base64-encoded X-PAYMENT header string required by the RPC Server.
        
        Args:
            requirement: The dictionary payload specifying the transaction cost, 
                         nonce, and destination address provided by the gateway.
                         
        Returns:
            str: The fully formatted, Base64-encoded header value.
        """
        if not self.signer:
            logger.error("Cannot sign X402 payment envelope: Signer is offline.")
            return None

        if not requirement:
            logger.warning("Empty payment requirement passed to X402 signer.")
            return None

        await append_agent_log(f"[{self.agent_name}] Generating X402 cryptographic payment envelope...")

        try:
            # 1. Produce the signature dictionary from the incoming target requirement
            envelope = sign_solana_payment(requirement, self.signer)
            
            # 2. Stringify the JSON structure with zero whitespace to ensure hash integrity
            json_str = json.dumps(envelope, separators=(',', ':'))
            
            # 3. Base64-encode the payload to build the HTTP header value
            x_payment_header_value = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
            
            await append_agent_log(f"[{self.agent_name}] X402 payment envelope successfully signed and encoded.")
            return x_payment_header_value
            
        except Exception as e:
            logger.error(f"Cryptographic signing failure during X402 envelope generation: {e}", exc_info=True)
            await append_agent_log(f"[{self.agent_name}] Fatal error signing X402 transaction payload.", level="ERROR")
            return None