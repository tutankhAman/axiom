"""EnergyPlus simulation driver encapsulating runtime callbacks and lifecycle management."""

import logging
import os
from collections.abc import Callable
from typing import Any

from pyenergyplus.api import EnergyPlusAPI

from sim.actuators import ActuatorManager
from sim.sensors import SensorManager, SimulationState

logger = logging.getLogger(__name__)

DEFAULT_ZONES = [
    "Core_ZN",
    "Perimeter_ZN_1",
    "Perimeter_ZN_2",
    "Perimeter_ZN_3",
    "Perimeter_ZN_4",
]

DEFAULT_ACTUATOR_SCHEDULES = [
    "HTGSETP_SCH_NO_OPTIMUM",
    "CLGSETP_SCH_NO_OPTIMUM",
    "HTGSETP_SCH_NO_OPTIMUM_w_SB",
    "CLGSETP_SCH_NO_OPTIMUM_w_SB",
]


class EnergyPlusDriver:
    """Manages EnergyPlus simulation execution, sensor/actuator state collection, and callbacks."""

    def __init__(
        self,
        idf_path: str,
        epw_path: str,
        output_dir: str = "output",
        zone_names: list[str] | None = None,
        actuator_schedules: list[str] | None = None,
        on_timestep: Callable[[SimulationState], None] | None = None,
        on_actuate: Callable[[Any, ActuatorManager], None] | None = None,
    ) -> None:
        self.idf_path = os.path.abspath(idf_path)
        self.epw_path = os.path.abspath(epw_path)
        self.output_dir = os.path.abspath(output_dir)
        self.zone_names = DEFAULT_ZONES if zone_names is None else zone_names
        self.actuator_schedules = (
            DEFAULT_ACTUATOR_SCHEDULES if actuator_schedules is None else actuator_schedules
        )
        self.on_timestep = on_timestep
        self.on_actuate = on_actuate

        self.api = EnergyPlusAPI()
        self.sensor_manager = SensorManager(self.api)
        self.actuator_manager = ActuatorManager(self.api)

        self.history: list[SimulationState] = []
        self.run_completed = False
        self.exit_code = -1
        self.callback_error: Exception | None = None

    def _actuation_callback(self, state: Any) -> None:
        """Callback triggered at the beginning of each zone timestep before heat balance init."""
        if self.callback_error is not None:
            return

        if self.api.exchange.warmup_flag(state) != 0:
            return

        try:
            if self.actuator_schedules:
                self.actuator_manager.init_handles(state, self.actuator_schedules)

            if self.on_actuate:
                self.on_actuate(state, self.actuator_manager)
        except Exception as e:
            if self.callback_error is None:
                self.callback_error = e
                logger.error("Error in simulation actuation callback: %s", e, exc_info=True)

    def _timestep_callback(self, state: Any) -> None:
        """Callback triggered at the end of each zone timestep after reporting."""
        if self.callback_error is not None:
            return

        if self.api.exchange.warmup_flag(state) != 0:
            return

        # Ensure only actual RunPeriod weather simulation timesteps are recorded
        if self.api.exchange.kind_of_sim(state) != 3:
            return

        try:
            sim_state = self.sensor_manager.fetch_state(state, self.zone_names)
            self.history.append(sim_state)

            if self.on_timestep:
                self.on_timestep(sim_state)
            else:
                zones_summary = ", ".join(
                    f"{z}: {data.mean_air_temp}°C (PMV: {data.pmv})"
                    for z, data in sim_state.zones.items()
                )
                logger.info(
                    "[Time: %.2fh] Outdoor: %.1f°C | HVAC: %.1fW | Zones: %s",
                    sim_state.sim_time_hours,
                    sim_state.outdoor_temp,
                    sim_state.hvac_power_w,
                    zones_summary,
                )
        except Exception as e:
            if self.callback_error is None:
                self.callback_error = e
                logger.error("Error in simulation timestep callback: %s", e, exc_info=True)

    def run(self) -> int:
        """Execute EnergyPlus simulation synchronously."""
        logger.info("Starting EnergyPlus run: IDF=%s, EPW=%s", self.idf_path, self.epw_path)
        os.makedirs(self.output_dir, exist_ok=True)

        self.history = []
        self.run_completed = False
        self.callback_error = None

        state = self.api.state_manager.new_state()

        # Register actuation callback before heat balance init
        if self.on_actuate or self.actuator_schedules:
            self.api.runtime.callback_begin_zone_timestep_before_init_heat_balance(
                state,
                self._actuation_callback,  # ty: ignore[invalid-argument-type]
            )

        # Register sensor callback for zone reporting timestep
        self.api.runtime.callback_end_zone_timestep_after_zone_reporting(
            state,
            self._timestep_callback,  # ty: ignore[invalid-argument-type]
        )

        cmd_args: list[str | bytes] = [
            "-d",
            self.output_dir,
            "-w",
            self.epw_path,
            self.idf_path,
        ]

        try:
            self.exit_code = self.api.runtime.run_energyplus(state, cmd_args)
            if self.callback_error is not None:
                raise self.callback_error
            self.run_completed = True
            logger.info("EnergyPlus simulation finished with exit code: %d", self.exit_code)
            return self.exit_code
        finally:
            self.api.state_manager.delete_state(state)
            logger.debug("Cleaned up EnergyPlus simulation state.")
