import os

import pytest

pytest.importorskip("pyenergyplus")


@pytest.mark.integration
def test_energyplus_driver_integration(tmp_path):
    from sim.driver import EnergyPlusDriver

    output_dir = str(tmp_path / "sim_output")
    idf_path = "models/baseline.idf"
    epw_path = "models/weather.epw"

    driver = EnergyPlusDriver(
        idf_path=idf_path,
        epw_path=epw_path,
        output_dir=output_dir,
    )

    exit_code = driver.run()

    # Assertion 1: Exit code is 0
    assert exit_code == 0, f"EnergyPlus simulation failed with exit code {exit_code}"
    assert driver.run_completed is True

    # Assertion 2: Sensor data collected and data integrity bounds
    assert len(driver.history) > 0, "No timestep history recorded"

    for step in driver.history:
        # Check global outdoor temp physically plausible
        assert -60.0 <= step.outdoor_temp <= 60.0, f"Unusual outdoor temp: {step.outdoor_temp}"
        assert step.hvac_power_w >= 0.0, f"Negative HVAC power: {step.hvac_power_w}"

        # Check zone states
        assert len(step.zones) == len(driver.zone_names), (
            f"Expected {len(driver.zone_names)} zones, got {len(step.zones)}"
        )
        for zone_name, zone_data in step.zones.items():
            assert 0.0 <= zone_data.mean_air_temp <= 50.0, (
                f"Zone {zone_name} temp out of bounds: {zone_data.mean_air_temp}"
            )
            assert -5.0 <= zone_data.pmv <= 5.0, (
                f"Zone {zone_name} PMV out of bounds: {zone_data.pmv}"
            )
            assert 0.0 <= zone_data.ppd <= 100.0, (
                f"Zone {zone_name} PPD out of bounds: {zone_data.ppd}"
            )

    # Assertion 3: Standard output files generated
    err_file = os.path.join(output_dir, "eplusout.err")
    assert os.path.exists(err_file), f"Output error log {err_file} missing"
