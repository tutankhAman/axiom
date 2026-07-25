"""Unit tests for simulation sensor manager and data structures."""

from unittest.mock import MagicMock

import pytest

from sim.sensors import InvalidSensorHandleError, SensorManager, SimulationState, ZoneState


def test_zone_state_dataclass():
    zone = ZoneState(zone_name="Core_ZN", mean_air_temp=21.5, pmv=0.1, ppd=5.2)
    assert zone.zone_name == "Core_ZN"
    assert zone.mean_air_temp == 21.5
    assert zone.pmv == 0.1
    assert zone.ppd == 5.2


def test_sensor_manager_initialize_success():
    mock_api = MagicMock()
    # Mock handle returns
    mock_api.exchange.get_variable_handle.side_effect = lambda state, name, key: 100

    manager = SensorManager(mock_api)
    manager.initialize_handles("dummy_state", ["Core_ZN"])

    assert manager.handles_initialized is True
    assert manager._outdoor_temp_handle == 100
    assert manager._zone_handles["Core_ZN"]["temp"] == 100


def test_sensor_manager_missing_outdoor_temp_raises_error():
    mock_api = MagicMock()
    # Mock outdoor temp returns -1 (handle missing)
    mock_api.exchange.get_variable_handle.return_value = -1

    manager = SensorManager(mock_api)
    with pytest.raises(InvalidSensorHandleError, match="Site Outdoor Air Drybulb Temperature"):
        manager.initialize_handles("dummy_state", ["Core_ZN"])


def test_sensor_manager_fetch_state():
    mock_api = MagicMock()
    mock_api.exchange.get_variable_handle.side_effect = lambda state, name, key: 42
    mock_api.exchange.day_of_year.return_value = 1
    mock_api.exchange.current_time.return_value = 12.0

    # Values for outdoor temp, hvac power, mean temp, pmv, ppd
    mock_api.exchange.get_variable_value.side_effect = [15.5, 1200.0, 22.0, -0.1, 6.0]

    manager = SensorManager(mock_api)
    sim_state = manager.fetch_state("dummy_state", ["Core_ZN"])

    assert isinstance(sim_state, SimulationState)
    assert sim_state.sim_time_hours == 12.0  # (1 - 1) days * 24 + 12
    assert sim_state.outdoor_temp == 15.5
    assert sim_state.hvac_power_w == 1200.0
    assert "Core_ZN" in sim_state.zones
    assert sim_state.zones["Core_ZN"].mean_air_temp == 22.0
    assert sim_state.zones["Core_ZN"].pmv == -0.1
    assert sim_state.zones["Core_ZN"].ppd == 6.0
