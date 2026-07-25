"""Integration tests for EnergyPlus simulation driver and actuator overrides."""

import os
from typing import Any

from sim.actuators import ActuatorManager, ZoneSetpoints
from sim.driver import EnergyPlusDriver


def test_energyplus_driver_baseline_integration(tmp_path):
    """Verify baseline un-actuated simulation run completes cleanly."""
    output_dir = str(tmp_path / "baseline_output")
    idf_path = "models/baseline.idf"
    epw_path = "models/weather.epw"

    driver = EnergyPlusDriver(
        idf_path=idf_path,
        epw_path=epw_path,
        output_dir=output_dir,
    )

    exit_code = driver.run()

    assert exit_code == 0, f"EnergyPlus baseline simulation failed with exit code {exit_code}"
    assert driver.run_completed is True
    assert len(driver.history) > 0

    for step in driver.history:
        assert -60.0 <= step.outdoor_temp <= 60.0
        assert step.hvac_power_w >= 0.0
        assert len(step.zones) == 5
        for zone_data in step.zones.values():
            assert 0.0 <= zone_data.mean_air_temp <= 50.0
            assert -5.0 <= zone_data.pmv <= 5.0
            assert 0.0 <= zone_data.ppd <= 100.0

    err_file = os.path.join(output_dir, "eplusout.err")
    assert os.path.exists(err_file)


def test_energyplus_actuator_override_integration(tmp_path):
    """Verify actuator overrides alter zone thermal response compared to baseline."""
    baseline_dir = str(tmp_path / "baseline_run")
    actuated_dir = str(tmp_path / "actuated_run")
    idf_path = "models/baseline.idf"
    epw_path = "models/weather.epw"

    # 1. Run baseline
    baseline_driver = EnergyPlusDriver(
        idf_path=idf_path,
        epw_path=epw_path,
        output_dir=baseline_dir,
    )
    assert baseline_driver.run() == 0

    # 2. Run actuated with elevated heating setpoint (26.0°C)
    def hardcoded_actuation(state: Any, manager: ActuatorManager) -> None:
        setpoints = ZoneSetpoints(heating_c=26.0, cooling_c=28.0)
        manager.set_zone_setpoints(
            state, "HTGSETP_SCH_NO_OPTIMUM", "CLGSETP_SCH_NO_OPTIMUM", setpoints
        )
        manager.set_zone_setpoints(
            state, "HTGSETP_SCH_NO_OPTIMUM_w_SB", "CLGSETP_SCH_NO_OPTIMUM_w_SB", setpoints
        )

    actuated_driver = EnergyPlusDriver(
        idf_path=idf_path,
        epw_path=epw_path,
        output_dir=actuated_dir,
        on_actuate=hardcoded_actuation,
    )
    assert actuated_driver.run() == 0

    # 3. Compare Core_ZN mean air temperature average
    baseline_temps = [step.zones["Core_ZN"].mean_air_temp for step in baseline_driver.history]
    actuated_temps = [step.zones["Core_ZN"].mean_air_temp for step in actuated_driver.history]

    avg_baseline = sum(baseline_temps) / len(baseline_temps)
    avg_actuated = sum(actuated_temps) / len(actuated_temps)

    # Actuated run heating setpoint at 26°C must increase zone temperature significantly
    assert avg_actuated > avg_baseline + 1.5, (
        f"Actuation failed to alter physics: Baseline avg={avg_baseline:.2f}°C, "
        f"Actuated avg={avg_actuated:.2f}°C"
    )
