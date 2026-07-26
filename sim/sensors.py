"""Sensor management and state data structures for EnergyPlus simulation."""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


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
    is_occupied: bool = True
    cumulative_hvac_kwh: float = 0.0
    zones: dict[str, ZoneState] = field(default_factory=dict)


class SensorManager:
    """Manages EnergyPlus variable handles and reads state snapshots safely."""

    def __init__(self, api: Any) -> None:
        self.api = api
        self.handles_initialized = False

        # Global handles
        self._outdoor_temp_handle: int = -1
        self._hvac_power_handle: int = -1
        self._hvac_meter_handle: int = -1
        self._fan_power_handle: int = -1
        self._cool_power_handle: int = -1
        self._heat_power_handle: int = -1

        # RunPeriod tracking
        self._start_day_of_year: int | None = None
        self._cumulative_hvac_kwh: float = 0.0
        self._last_time_hours: float = 0.0

        # Per-zone sensor handles: zone_name -> Dict[var_name, handle_int]
        self._zone_handles: dict[str, dict[str, int]] = {}

    def reset(self) -> None:
        """Clear run-period tracking state for a fresh simulation run."""
        self._start_day_of_year = None
        self._last_time_hours = 0.0
        self._cumulative_hvac_kwh = 0.0

    def initialize_handles(self, state: Any, zone_names: list[str]) -> None:
        """Fetch and cache variable handles from EnergyPlus runtime exchange API."""
        logger.info("Initializing EnergyPlus sensor handles for zones: %s", zone_names)

        if not self.handles_initialized:
            # 1. Meter Handle (Electricity:HVAC)
            self._hvac_meter_handle = self.api.exchange.get_meter_handle(state, "Electricity:HVAC")

            # 2. Outdoor Temp Handle
            self._outdoor_temp_handle = self.api.exchange.get_variable_handle(
                state, "Site Outdoor Air Drybulb Temperature", "Environment"
            )
            if self._outdoor_temp_handle == -1:
                self._outdoor_temp_handle = self.api.exchange.get_variable_handle(
                    state, "Site Outdoor Air Drybulb Temperature", "*"
                )

            # 3. Component HVAC Power Handles (Fallbacks)
            self._hvac_power_handle = self.api.exchange.get_variable_handle(
                state, "Facility Total HVAC Electricity Demand Rate", "*"
            )
            self._fan_power_handle = self.api.exchange.get_variable_handle(
                state, "Fan Electricity Rate", "*"
            )
            self._cool_power_handle = self.api.exchange.get_variable_handle(
                state, "Cooling Coil Electricity Rate", "*"
            )
            self._heat_power_handle = self.api.exchange.get_variable_handle(
                state, "Heating Coil Electricity Rate", "*"
            )

        # Per-Zone Handles
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

        # Track RunPeriod start day to ensure relative time starts at 0.0h
        current_day = self.api.exchange.day_of_year(state)
        if self._start_day_of_year is None and not self.api.exchange.warmup_flag(state):
            self._start_day_of_year = current_day

        start_day = self._start_day_of_year if self._start_day_of_year is not None else current_day
        day_offset = current_day - start_day
        current_time_hours = day_offset * 24.0 + self.api.exchange.current_time(state)

        # Read HVAC Power in Watts
        hvac_power = 0.0
        if self._hvac_meter_handle != -1:
            joules = self.api.exchange.get_meter_value(state, self._hvac_meter_handle)
            # Derive timestep from EnergyPlus zone_time_step (reports in hours)
            ts_hours = self.api.exchange.zone_time_step(state)
            hvac_power = joules / (ts_hours * 3600.0) if ts_hours > 0 else joules / 900.0
        elif self._hvac_power_handle != -1:
            hvac_power = self.api.exchange.get_variable_value(state, self._hvac_power_handle)
        else:
            fan_p = (
                self.api.exchange.get_variable_value(state, self._fan_power_handle)
                if self._fan_power_handle != -1
                else 0.0
            )
            cool_p = (
                self.api.exchange.get_variable_value(state, self._cool_power_handle)
                if self._cool_power_handle != -1
                else 0.0
            )
            heat_p = (
                self.api.exchange.get_variable_value(state, self._heat_power_handle)
                if self._heat_power_handle != -1
                else 0.0
            )
            hvac_power = fan_p + cool_p + heat_p

        # Outdoor Temperature
        outdoor_temp = (
            self.api.exchange.get_variable_value(state, self._outdoor_temp_handle)
            if self._outdoor_temp_handle != -1
            else 20.0
        )

        hour = int(current_time_hours % 24)
        day_of_week = (
            self.api.exchange.day_of_week(state) if hasattr(self.api.exchange, "day_of_week") else 2
        )
        is_weekend = day_of_week == 1 or day_of_week == 7  # 1 = Sunday, 7 = Saturday
        is_occupied = (not is_weekend) and (7 <= hour < 19)

        if self._last_time_hours > 0:
            dt = current_time_hours - self._last_time_hours
            if dt > 0:
                self._cumulative_hvac_kwh += (hvac_power * dt) / 1000.0
        self._last_time_hours = current_time_hours

        # Zone metrics
        zones_data: dict[str, ZoneState] = {}
        for zone in zone_names:
            h = self._zone_handles[zone]
            temp_val = (
                self.api.exchange.get_variable_value(state, h["temp"]) if h["temp"] != -1 else 22.0
            )
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
            sim_time_hours=round(float(current_time_hours), 2),
            outdoor_temp=round(float(outdoor_temp), 2),
            hvac_power_w=round(float(hvac_power), 2),
            is_occupied=is_occupied,
            cumulative_hvac_kwh=round(self._cumulative_hvac_kwh, 3),
            zones=zones_data,
        )
