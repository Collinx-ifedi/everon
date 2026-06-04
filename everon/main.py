# main.py

from __future__ import annotations

import os
import sys
import asyncio
import logging
from logging.handlers import RotatingFileHandler

from config import settings
from engine.scheduler import EveronBackgroundScheduler
from utils.file_manager import append_agent_log

# -------------------------------------------------------------------------
# Production Logging Infrastructure Setup
# -------------------------------------------------------------------------
def setup_production_logging() -> logging.Logger:
    """
    Configures an enterprise-grade hierarchical logging system with 
    simultaneous console stdout output and thread-safe file rotation 
    to manage disk space boundaries seamlessly.
    """
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    
    logger = logging.getLogger("EveronAgent")
    logger.setLevel(logging.INFO)
    logger.propagate = False  # Avoid double logging bubbles to the root logger

    # Clean existing handlers to ensure fresh runtime instantiation
    if logger.handlers:
        logger.handlers.clear()

    log_format = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] (%(filename)s:%(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Thread-safe Rotating File Handler (Max 10MB per file, rotating across 5 files)
    log_file_path = os.path.join(settings.DATA_DIR, "system_runtime.log")
    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=10 * 1024 * 1024, 
        backupCount=5, 
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    # 2. Standard Output Stream Handler for real-time process monitoring
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    return logger


# Initialize production loggers immediately on process entry
logger = setup_production_logging()


# -------------------------------------------------------------------------
# Main Asynchronous Process Core
# -------------------------------------------------------------------------
async def run_everon_application() -> None:
    """
    Pre-checks runtime conditions, synchronizes data infrastructure directories,
    and mounts the non-blocking autonomous background daemon execution frame.
    """
    agent_name = getattr(settings, "AGENT_NAME", "Everon")
    
    sys.stdout.write(r"""
 _____                               
|  ___|                              
| |__ __   __ ___  _ __  ___   _ __  
|  __|\ \ / // _ \| '__|/ _ \ | '_ \ 
| |___ \ V /|  __/| |  | (_) || | | |
\____/  \_/  \___||_|   \___/ |_| |_|
    """)
    sys.stdout.write(f"\n--- {agent_name} Autonomous Backend Engine Initialization ---\n\n")
    sys.stdout.flush()

    # Enforce atomic data enclave checks before ignition
    try:
        os.makedirs(settings.DATA_DIR, exist_ok=True)
        await append_agent_log(f"[{agent_name}] Core system runtime folders validated successfully.")
    except Exception as e:
        logger.critical(f"Data directory generation failure at path [{settings.DATA_DIR}]: {e}")
        sys.exit(1)

    # Verify cryptographic runtime capability parameters
    if not settings.SOLANA_WALLET_ADDRESS:
        logger.critical("Initialization aborted: SOLANA_WALLET_ADDRESS parameter validation failed.")
        sys.exit(1)

    # Instantiate the core daemon scheduler worker frame
    scheduler = EveronBackgroundScheduler()
    
    await append_agent_log(f"[{agent_name}] Boot sequence verified. Handing thread orchestration to the scheduler daemon.")
    
    try:
        # Ignite the continuous 120-second sequential asset tracking processor
        await scheduler.start()
        
    except asyncio.CancelledError:
        # Intercepted cleanly when task cancellation cascades through the runtime loop
        logger.info("Main worker orchestration loop received task cancellation instruction.")
    except Exception as e:
        logger.critical(f"Unhandled runtime catastrophe inside primary thread context: {e}", exc_info=True)
        await append_agent_log(f"[{agent_name}] Core runtime exception encountered in main thread block.", level="ERROR")
        raise e
    finally:
        await append_agent_log(f"[{agent_name}] Core worker threads successfully insulated. System state: OFFLINE.")


# -------------------------------------------------------------------------
# Application Ignition Wrapper
# -------------------------------------------------------------------------
def main() -> None:
    """
    Definitive process entry point. Launches the asyncio loop environment,
    configures clean exception handlers, and intercepts catastrophic failure codes.
    """
    if sys.platform == "win32":
        # Enforce ProactorEventLoop policy on Windows to support non-blocking subprocess pipes natively
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        asyncio.run(run_everon_application())
    except KeyboardInterrupt:
        # Handles user-triggered exit signals (Ctrl+C) gracefully outside the loop context if caught late
        sys.stdout.write("\n[Everon] KeyboardInterrupt caught at root level. Winding down background loops safely.\n")
        sys.stdout.flush()
    except Exception as e:
        sys.stderr.write(f"\n[FATAL KERNEL PANIC] Application collapsed during primary loop execution: {e}\n")
        sys.stderr.flush()
        sys.exit(1)


if __name__ == "__main__":
    main()