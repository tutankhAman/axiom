"""Actuator management for EnergyPlus simulation schedule overrides."""

import logging
from dataclasses import dataclass
from typing import Any

from pyenergyplus.api import EnergyPlusAPI

logger = logging.getLogger(__name__)


class InvalidActuatorHandleError(Exception):
    """Raised when EnergyPlus fails to return a valid actuator handle."""


@dataclass(frozen=True)
class ZoneSetpoints:
    """Heating and cooling setpoint temperatures in Celsius."""

    heating_c: float
    cooling_c: float


class ActuatorManager:
    """Manages acquisition and modification of EnergyPlus actuator handles."""

    SUPPORTED_COMPONENT_TYPES = ["Schedule:Compact", "Schedule:Constant", "Schedule"]

    def __init__(self, api: EnergyPlusAPI) -> None:
        self.api = api
        self.handles: dict[str, int] = {}
        self.initialized = False

    def init_handles(self, state: Any, schedule_names: list[str]) -> None:
        """Fetch and cache actuator handles for specified schedule names."""
        missing_schedules = [name for name in schedule_names if name not in self.handles]
        if not missing_schedules:
            return

        for name in missing_schedules:
            handle = -1
            for comp_type in self.SUPPORTED_COMPONENT_TYPES:
                handle = self.api.exchange.get_actuator_handle(
                    state, comp_type, "Schedule Value", name
                )
                if handle != -1:
                    logger.debug("Found actuator handle %d for '%s' (%s)", handle, name, comp_type)
                    break

            if handle == -1:
                raise InvalidActuatorHandleError(
                    f"Failed to resolve actuator handle for schedule '{name}'."
                )

            self.handles[name] = handle

        self.initialized = True
        logger.info("Successfully initialized %d actuator handles.", len(self.handles))

    def set_schedule_value(self, state: Any, schedule_name: str, value: float) -> None:
        """Write a target value to a specific schedule actuator."""
        if not self.initialized:
            raise InvalidActuatorHandleError("ActuatorManager handles have not been initialized.")

        if schedule_name not in self.handles:
            raise InvalidActuatorHandleError(
                f"Schedule '{schedule_name}' was not registered during initialization."
            )

        handle = self.handles[schedule_name]
        self.api.exchange.set_actuator_value(state, handle, value)

    def set_zone_setpoints(
        self,
        state: Any,
        htg_schedule: str,
        clg_schedule: str,
        setpoints: ZoneSetpoints,
    ) -> None:
        """Write heating and cooling setpoint temperatures for a zone's schedules."""
        self.set_schedule_value(state, htg_schedule, setpoints.heating_c)
        self.set_schedule_value(state, clg_schedule, setpoints.cooling_c)
