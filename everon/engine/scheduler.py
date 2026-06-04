# scheduler.py

from __future__ import annotations
import sys
import os
from pathlib import Path
import asyncio
import logging
import signal
import sys
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from config import settings
from engine.workflow import EveronWorkflowProcessor
from utils.file_manager import append_agent_log

logger = logging.getLogger("EveronAgent")


class EveronBackgroundScheduler:
    """
    Autonomous Non-Blocking Background Daemon for Everon.
    Orchestrates the market processing loops sequentially at an absolute
    cadence interval of 120 seconds. Handles graceful OS signal intercepts.
    """

    def __init__(self) -> None:
        self.agent_name = "Everon"
        self.workflow_processor = EveronWorkflowProcessor()
        
        # Absolute iteration cadence defined at exactly 120 seconds
        self.loop_interval_seconds = 120
        self.is_running = False
        
        # Standardized 10-coin target tracking index array
        self.tracking_index: List[str] = getattr(
            settings, 
            "TRACKING_INDEX", 
            ["SOL", "BTC", "ETH", "HYPE", "JUP", "PYTH", "RENDER", "BONK", "WIF", "DRIFT"]
        )

    async def start(self) -> None:
        """
        Activates the infinite non-blocking daemon process. Monitors system
        run states and enforces serial execution spacing.
        """
        if self.is_running:
            logger.warning("Scheduler execution cycle is already running active loops.")
            return

        self.is_running = True
        await append_agent_log(f"[{self.agent_name}] Daemon initialized. Target tracking index contains {len(self.tracking_index)} assets.")
        await append_agent_log(f"[{self.agent_name}] Scheduling execution sweeps continuously at a strict 120-second cadence interval.")

        # Setup OS level signal handling for graceful shutdown operations
        self._register_signal_handlers()

        while self.is_running:
            try:
                await append_agent_log(f"[{self.agent_name}] Waking daemon. Initiating sequential index scan cycle...")
                
                # Triggers the workflow manager to run through the coins sequentially
                # Individual token errors are isolated within the workflow layer internally
                await self.workflow_processor.execute_full_market_scan(tracking_tokens=self.tracking_index)
                
                await append_agent_log(f"[{self.agent_name}] Index scan cycle complete. Daemon entering sleep phase.")
                
            except Exception as e:
                logger.critical(f"Unhandled operational error inside scheduler main loop: {e}", exc_info=True)
                await append_agent_log(f"[{self.agent_name}] Critical core scheduler fault encountered.", level="ERROR")
            
            # Enforce non-blocking cadence interval sleep ticking
            await asyncio.sleep(self.loop_interval_seconds)

    def stop(self) -> None:
        """
        Gracefully flips the operational flag to wind down execution layers
        cleanly during the next sleep loop window.
        """
        logger.info("Graceful shutdown request received by scheduler daemon.")
        self.is_running = False

    def _register_signal_handlers(self) -> None:
        """
        Binds termination interrupt signals directly to the stop sequence
        to safeguard local file writes and atomic operations.
        """
        loop = asyncio.get_running_loop()
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda s=sig: self._handle_termination(s))
            except NotImplementedError:
                # Fallback protection layout for Windows environments where add_signal_handler is omitted
                pass

    def _handle_termination(self, sig: signal.Signals) -> None:
        """
        Handles signal catch states cleanly without panicking the active stack.
        """
        logger.info(f"Captured termination signal: {sig.name}. Triggering insulation sequences.")
        self.stop()
        
        # Print fallback notice for absolute tracking stability
        sys.stdout.write(f"\n[{self.agent_name}] Air-lock closure sequence engaged. Halting background loops safely...\n")
        sys.stdout.flush()


async def main() -> None:
    """
    Production entry point utility designed to run the scheduler standalone
    as an isolated background operating system worker thread or container daemon.
    """
    # Initialize basic console formatting if runtime logging hasn't booted yet
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    scheduler = EveronBackgroundScheduler()
    await scheduler.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)