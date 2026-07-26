"""In-memory thread-safe state bridge for decoupling EnergyPlus sim thread from agent thread."""

import logging
import threading
from collections import deque

from sim.sensors import SimulationState

logger = logging.getLogger(__name__)


class StateBridge:
    """Thread-safe state bridge encapsulating simulation state snapshots and actuation setpoints.

    Uses an in-process dictionary guarded by a threading.Lock and a threading.Event
    to signal the agent thread when pre-filter conditions are met.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest_state: SimulationState | None = None
        self._history: deque[dict] = deque(maxlen=3)
        # Actuation schedule map: schedule_name -> target_value
        self._actuation_commands: dict[str, float] = {}
        self._last_reason: str = ""
        self.trigger_event = threading.Event()

    def update_state(self, state: SimulationState) -> None:
        """Update the latest simulation state snapshot safely."""
        with self._lock:
            if self._latest_state is not None:
                # Add to history
                self._history.append(
                    {"state": self._latest_state, "setpoints": dict(self._actuation_commands)}
                )
            self._latest_state = state

    def get_latest_state(self) -> SimulationState | None:
        """Fetch a copy/reference of the latest simulation state safely."""
        with self._lock:
            return self._latest_state

    def get_history(self) -> list[dict]:
        """Fetch the rolling history of past states and their setpoints."""
        with self._lock:
            return list(self._history)

    def set_actuation_commands(self, commands: dict[str, float], reason: str = "") -> None:
        """Store target schedule actuation commands safely."""
        with self._lock:
            self._actuation_commands = dict(commands)
            if reason:
                self._last_reason = reason
        logger.debug("Updated actuation commands in StateBridge: %s (Reason: %s)", commands, reason)

    def get_actuation_commands(self) -> dict[str, float]:
        """Fetch a copy of current actuation schedule values (Zero-Order Hold)."""
        with self._lock:
            return dict(self._actuation_commands)

    def set_last_reason(self, reason: str) -> None:
        """Store the latest decision reason from LLM or prefilter."""
        with self._lock:
            self._last_reason = reason

    def get_last_reason(self) -> str:
        """Fetch the latest decision reason."""
        with self._lock:
            return self._last_reason

    def trigger(self) -> None:
        """Signal the agent thread that a decision evaluation is required."""
        self.trigger_event.set()
