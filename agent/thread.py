"""Background agent worker thread for decoupled execution."""

import logging
import threading

from bridge.state_bridge import StateBridge
from sim.sensors import SimulationState

logger = logging.getLogger(__name__)


class AgentThread(threading.Thread):
    """Background worker thread waiting on StateBridge events.

    Decouples simulation step processing from agent reasoning. In Phase 3,
    this thread wakes up when triggered and logs "would call LLM now".
    """

    def __init__(self, bridge: StateBridge, name: str = "AgentThread") -> None:
        super().__init__(name=name, daemon=True)
        self.bridge = bridge
        self._stop_event = threading.Event()
        self.trigger_count = 0
        self.invocations: list[SimulationState] = []

    def run(self) -> None:
        logger.info("AgentThread started and waiting for state bridge triggers.")

        # Instantiate orchestrator here so the thread owns the client
        from agent.orchestrator import LLMOrchestrator

        orchestrator = LLMOrchestrator(bridge=self.bridge)

        while not self._stop_event.is_set():
            # Wait for pre-filter trigger event with short timeout to allow graceful stop
            if self.bridge.trigger_event.wait(timeout=0.1):
                self.bridge.trigger_event.clear()
                state = self.bridge.get_latest_state()
                if state:
                    self.trigger_count += 1
                    self.invocations.append(state)
                    logger.info(
                        "AgentThread [Trigger #%d] at %.2fh: evaluating with LLM...",
                        self.trigger_count,
                        state.sim_time_hours,
                    )
                    orchestrator.evaluate_and_act()

        logger.info("AgentThread stopped.")

    def stop(self, timeout: float | None = 2.0) -> None:
        """Signal the agent thread to terminate and wait for exit."""
        self._stop_event.set()
        # Ensure trigger_event doesn't keep thread waiting during stop
        self.bridge.trigger_event.set()
        self.join(timeout=timeout)
