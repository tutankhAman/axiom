"""Deterministic pre-filter for evaluating simulation state triggers without calling the LLM."""

import logging
from dataclasses import dataclass

from sim.sensors import SimulationState

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PreFilterDecision:
    """Outcome of pre-filter rule evaluation."""

    should_trigger: bool
    reason: str
    setback_command: dict[str, float] | None = None


class PreFilter:
    """Rule-based pre-filter to decide when to wake the agent thread.

    Triggers under two conditions:
    1. Comfort band violation: Any zone's PMV is outside [pmv_min, pmv_max] (default: [-0.5, 0.5]).
    2. Periodic control interval: At least interval_hours have passed since the last trigger.
    """

    def __init__(
        self,
        interval_hours: float = 1.0,
        pmv_min: float = -0.5,
        pmv_max: float = 0.5,
        min_cooldown_hours: float = 0.0,
    ) -> None:
        self.interval_hours = interval_hours
        self.pmv_min = pmv_min
        self.pmv_max = pmv_max
        self.min_cooldown_hours = min_cooldown_hours
        self.last_trigger_time: float | None = None

    def evaluate(self, state: SimulationState) -> PreFilterDecision:
        """Evaluate simulation state against deterministic trigger rules."""

        # Handle time reset between Sizing Period and actual RunPeriod
        if self.last_trigger_time is not None and state.sim_time_hours < self.last_trigger_time:
            logger.info("Simulation time reset detected. Clearing trigger history.")
            self.last_trigger_time = None

        # Deterministic night setback: bypass LLM entirely for all unoccupied hours.
        # Pre-cooling was removed — this building's short thermal time constant means
        # pre-cooling energy cost exceeds any peak-shift benefit.
        if not state.is_occupied:
            return PreFilterDecision(
                should_trigger=False,
                reason="Unoccupied hour: deterministic night setback active (cool=30.0°C)",
                setback_command={"heat": 15.0, "cool": 30.0},
            )

        # Enforce minimum cooldown between any triggers
        if self.last_trigger_time is not None and (
            state.sim_time_hours - self.last_trigger_time
        ) < (self.min_cooldown_hours - 1e-5):
            return PreFilterDecision(
                should_trigger=False,
                reason=f"Cooldown active ({self.min_cooldown_hours}h)",
            )

        # Rule 1: Comfort constraint violation in any zone
        for zone_name, zone_state in state.zones.items():
            if zone_state.pmv < self.pmv_min or zone_state.pmv > self.pmv_max:
                reason = (
                    f"Zone '{zone_name}' PMV ({zone_state.pmv}) outside comfort band "
                    f"[{self.pmv_min}, {self.pmv_max}]"
                )
                self.last_trigger_time = state.sim_time_hours
                logger.info("[Time %.2fh] PreFilter trigger: %s", state.sim_time_hours, reason)
                return PreFilterDecision(should_trigger=True, reason=reason)

        # Rule 2: Fixed periodic control interval check
        if self.last_trigger_time is None or (state.sim_time_hours - self.last_trigger_time) >= (
            self.interval_hours - 1e-5
        ):
            reason = (
                "Initial trigger"
                if self.last_trigger_time is None
                else f"Control interval elapsed ({self.interval_hours}h)"
            )
            self.last_trigger_time = state.sim_time_hours
            logger.info("[Time %.2fh] PreFilter trigger: %s", state.sim_time_hours, reason)
            return PreFilterDecision(should_trigger=True, reason=reason)

        return PreFilterDecision(
            should_trigger=False,
            reason="Within comfort bounds and control interval has not elapsed",
        )
