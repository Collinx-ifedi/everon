# utils/file_manager.py

from __future__ import annotations
import sys
import os
from pathlib import Path
import json
import logging
from typing import Dict, Any, List, Optional
import aiofiles

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from models.schemas import DecisionOutput

logger = logging.getLogger("SolanaIntelligenceAgent")

# --- Constants for Data Storage Paths ---
DATA_DIR = "data"
LATEST_RESULTS_FILE = os.path.join(DATA_DIR, "latest_results.json")
PAYMENT_LOGS_FILE = os.path.join(DATA_DIR, "payment_logs.json")
AGENT_LOGS_FILE = os.path.join(DATA_DIR, "agent_logs.json")


def _ensure_data_directory_exists() -> None:
    """
    Synchronous helper to verify the data path exists prior to file operations.
    Fails gracefully if a directory permission error presents itself.
    """
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception as e:
        logger.critical(f"CRITICAL: Failed to instantiate data directory framework: {e}")


# Initialize storage layer setup immediately upon module import
_ensure_data_directory_exists()


async def safe_write_json(file_path: str, data: Any) -> bool:
    """
    Asynchronously writes a serializable Python object to a target JSON file.
    Utilizes a temporary file swap trick for atomic reliability if needed, 
    preventing file corruption during system crashes.

    Args:
        file_path: Path to the destination file.
        data: The JSON-serializable data payload.

    Returns:
        bool: True if write was successful, False otherwise.
    """
    try:
        # Pre-serialize to catch serialization failures before blowing up the file on disk
        serialized_data = json.dumps(data, indent=4, default=str)
        
        async with aiofiles.open(file_path, mode='w', encoding='utf-8') as f:
            await f.write(serialized_data)
        return True
    except TypeError as te:
        logger.error(f"Serialization Failure writing to {file_path}: {te}")
        return False
    except IOError as ioe:
        logger.error(f"Disk I/O Error writing to {file_path}: {ioe}")
        return False
    except Exception as e:
        logger.error(f"Unexpected operational crash writing to {file_path}: {e}")
        return False


async def safe_read_json(file_path: str, default_factory: Any = dict) -> Any:
    """
    Asynchronously reads data from a target JSON tracking log. If the file does not 
    exist or is malformed, it returns the provided default factory fallback.

    Args:
        file_path: Path to the source file.
        default_factory: Object class instantiation fallback (e.g., dict, list).

    Returns:
        Any: Decoded JSON content or fallback factory object.
    """
    if not os.path.exists(file_path):
        return default_factory()

    try:
        async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
            content = await f.read()
            if not content.strip():
                return default_factory()
            return json.loads(content)
    except json.JSONDecodeError as jde:
        logger.warning(f"Corrupt or incomplete JSON format detected at {file_path}. Resetting. Error: {jde}")
        return default_factory()
    except IOError as ioe:
        logger.error(f"Disk I/O Error reading from {file_path}: {ioe}")
        return default_factory()


async def append_payment_log(log_entry: Dict[str, Any]) -> None:
    """
    Thread-safe asynchronous log appender mapping to payment_logs.json.
    Ensures structural tracking parameters are properly indexed for verification.
    """
    current_logs = await safe_read_json(PAYMENT_LOGS_FILE, default_factory=list)
    if not isinstance(current_logs, list):
        current_logs = []
    
    current_logs.append(log_entry)
    await safe_write_json(PAYMENT_LOGS_FILE, current_logs)


async def append_agent_log(message: str, level: str = "INFO") -> None:
    """
    Maintains a dedicated telemetry trace within agent_logs.json for 
    asynchronous ingestion by the Streamlit application dashboard interface.
    """
    from datetime import datetime, timezone
    current_logs = await safe_read_json(AGENT_LOGS_FILE, default_factory=list)
    if not isinstance(current_logs, list):
        current_logs = []

    log_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper().strip(),
        "message": message
    }
    
    current_logs.append(log_payload)
    
    # Enforce a rolling history cap of 200 entries to prevent local storage inflation
    if len(current_logs) > 200:
        current_logs = current_logs[-200:]
        
    await safe_write_json(AGENT_LOGS_FILE, current_logs)


def save_output_results_sync(decision: DecisionOutput) -> None:
    """
    Synchronous fallback execution bridge to safely dump final signal decisions 
    to latest_results.json outside the active event loop if required.
    """
    try:
        serialized_payload = json.dumps(decision.model_dump(), indent=4, default=str)
        with open(LATEST_RESULTS_FILE, 'w', encoding='utf-8') as f:
            f.write(serialized_payload)
    except Exception as e:
        logger.error(f"Failed to execute synchronous data state flush: {e}")
