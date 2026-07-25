"""Sensor management and state data structures for EnergyPlus simulation."""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class InvalidSensorHandleError(Exception):
    """Raised when an EnergyPlus sensor variable handle fails to resolve (-1)."""

    pass


@dataclass(frozen=True)
class ZoneState:
    """Snapshot of a single building zone's thermal state."""

    zone_name: str
    mean_air_temp: float
    pmv: float
    ppd: float


@dataclass(frozen=True)
class SimulationState:
    """Snapshot of the overall building simulation state at a single timestep."""

    sim_time_hours: float
    outdoor_temp: float
    hvac_power_w: float
    zones: dict[str, ZoneState] = field(default_factory=dict)


class SensorManager:
    """Manages EnergyPlus variable handles and reads state snapshots safely."""

    def __init__(self, api: Any) -> None:
        self.api = api
        self.handles_initialized = False

        # Global sensor handles
        self._outdoor_temp_handle: int = -1
        self._hvac_power_handle: int = -1

        # Per-zone sensor handles: zone_name -> Dict[var_name, handle_int]
        self._zone_handles: dict[str, dict[str, int]] = {}

    def initialize_handles(self, state: Any, zone_names: list[str]) -> None:
        """Fetch and cache variable handles from EnergyPlus runtime exchange API.

        Must be called after API state initialization and warm-up completion.
        """
        logger.info("Initializing EnergyPlus sensor handles for zones: %s", zone_names)

        # 1. Global Handles
        if not self.handles_initialized:
            self._outdoor_temp_handle = self.api.exchange.get_variable_handle(
                state, "Site Outdoor Air Drybulb Temperature", "Environment"
            )
            self._hvac_power_handle = self.api.exchange.get_variable_handle(
                state, "Facility Total HVAC Electricity Demand Rate", "Whole Building"
            )

            if self._outdoor_temp_handle == -1:
                # Try key '*' if 'Environment' is missing
                self._outdoor_temp_handle = self.api.exchange.get_variable_handle(
                    state, "Site Outdoor Air Drybulb Temperature", "*"
                )

            if self._hvac_power_handle == -1:
                self._hvac_power_handle = self.api.exchange.get_variable_handle(
                    state, "Facility Total HVAC Electricity Demand Rate", "*"
                )

            if self._outdoor_temp_handle == -1:
                raise InvalidSensorHandleError(
                    "Could not locate variable handle for 'Site Outdoor Air Drybulb Temperature'"
                )

            # Note: HVAC demand rate handle may be -1 if HVAC system isn't running
            # or key differs; handle gracefully
            if self._hvac_power_handle == -1:
                logger.warning(
                    "HVAC Electricity Demand handle is -1; fallback to 0.0 W will be used."
                )

        # 2. Per-Zone Handles
        for zone in zone_names:
            if zone in self._zone_handles:
                continue

            temp_handle = self.api.exchange.get_variable_handle(
                state, "Zone Mean Air Temperature", zone
            )
            pmv_handle = self.api.exchange.get_variable_handle(
                state, "Zone Thermal Comfort Fanger Model PMV", zone
            )
            ppd_handle = self.api.exchange.get_variable_handle(
                state, "Zone Thermal Comfort Fanger Model PPD", zone
            )

            if temp_handle == -1:
                raise InvalidSensorHandleError(
                    f"Could not locate 'Zone Mean Air Temperature' handle for zone '{zone}'"
                )

            if pmv_handle == -1:
                logger.warning(
                    "PMV handle missing for zone '%s'. Fanger model enabled in IDF?", zone
                )
            if ppd_handle == -1:
                logger.warning("PPD handle missing for zone '%s'.", zone)

            self._zone_handles[zone] = {
                "temp": temp_handle,
                "pmv": pmv_handle,
                "ppd": ppd_handle,
            }

        self.handles_initialized = True
        logger.info("Successfully initialized sensor handles.")

    def fetch_state(self, state: Any, zone_names: list[str]) -> SimulationState:
        """Fetch current sensor readings from EnergyPlus shared memory state."""
        if not self.handles_initialized or any(
            zone not in self._zone_handles for zone in zone_names
        ):
            self.initialize_handles(state, zone_names)

        # Time tracking (compensate 1-based day_of_year to 0-based elapsed days)
        current_time = (
            self.api.exchange.day_of_year(state) - 1
        ) * 24.0 + self.api.exchange.current_time(state)

        # Global metrics
        outdoor_temp = self.api.exchange.get_variable_value(state, self._outdoor_temp_handle)
        hvac_power = (
            self.api.exchange.get_variable_value(state, self._hvac_power_handle)
            if self._hvac_power_handle != -1
            else 0.0
        )

        # Zone metrics
        zones_data: dict[str, ZoneState] = {}
        for zone in zone_names:
            h = self._zone_handles[zone]
            temp_val = self.api.exchange.get_variable_value(state, h["temp"])
            pmv_val = (
                self.api.exchange.get_variable_value(state, h["pmv"]) if h["pmv"] != -1 else 0.0
            )
            ppd_val = (
                self.api.exchange.get_variable_value(state, h["ppd"]) if h["ppd"] != -1 else 0.0
            )

            zones_data[zone] = ZoneState(
                zone_name=zone,
                mean_air_temp=round(float(temp_val), 2),
                pmv=round(float(pmv_val), 3),
                ppd=round(float(ppd_val), 2),
            )

        return SimulationState(
            sim_time_hours=round(float(current_time), 2),
            outdoor_temp=round(float(outdoor_temp), 2),
            hvac_power_w=round(float(hvac_power), 2),
            zones=zones_data,
        )
