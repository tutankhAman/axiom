"""In-memory thread-safe state bridge for decoupling EnergyPlus sim thread from agent thread."""

import logging
import threading

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
        # Actuation schedule map: schedule_name -> target_value
        self._actuation_commands: dict[str, float] = {}
        self.trigger_event = threading.Event()

    def update_state(self, state: SimulationState) -> None:
        """Update the latest simulation state snapshot safely."""
        with self._lock:
            self._latest_state = state

    def get_latest_state(self) -> SimulationState | None:
        """Fetch a copy/reference of the latest simulation state safely."""
        with self._lock:
            return self._latest_state

    def set_actuation_commands(self, commands: dict[str, float]) -> None:
        """Store target schedule actuation commands safely."""
        with self._lock:
            self._actuation_commands = dict(commands)
        logger.debug("Updated actuation commands in StateBridge: %s", commands)

    def get_actuation_commands(self) -> dict[str, float]:
        """Fetch a copy of current actuation schedule values (Zero-Order Hold)."""
        with self._lock:
            return dict(self._actuation_commands)

    def trigger(self) -> None:
        """Signal the agent thread that a decision evaluation is required."""
        self.trigger_event.set()
