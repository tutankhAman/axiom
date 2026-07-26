"""Unit tests for ActuatorManager and setpoint control."""

from unittest.mock import MagicMock

import pytest

from sim.actuators import ActuatorManager, InvalidActuatorHandleError, ZoneSetpoints


def test_zone_setpoints_dataclass():
    sp = ZoneSetpoints(heating_c=21.0, cooling_c=24.0)
    assert sp.heating_c == 21.0
    assert sp.cooling_c == 24.0


def test_actuator_manager_init_handles_success():
    mock_api = MagicMock()
    mock_api.exchange.get_actuator_handle.side_effect = lambda state, comp, ctrl, name: 50

    manager = ActuatorManager(mock_api)
    manager.init_handles("dummy_state", ["HTGSETP_SCH_NO_OPTIMUM"])

    assert manager.initialized is True
    assert manager.handles["HTGSETP_SCH_NO_OPTIMUM"] == 50


def test_actuator_manager_missing_handle_raises_error():
    mock_api = MagicMock()
    mock_api.exchange.get_actuator_handle.return_value = -1

    manager = ActuatorManager(mock_api)
    with pytest.raises(InvalidActuatorHandleError, match="Failed to resolve actuator handle"):
        manager.init_handles("dummy_state", ["HTGSETP_SCH_NO_OPTIMUM"])


def test_actuator_manager_set_schedule_value_uninitialized():
    mock_api = MagicMock()
    manager = ActuatorManager(mock_api)

    with pytest.raises(InvalidActuatorHandleError, match="handles have not been initialized"):
        manager.set_schedule_value("dummy_state", "HTGSETP_SCH_NO_OPTIMUM", 22.0)


def test_actuator_manager_set_schedule_value_unregistered():
    mock_api = MagicMock()
    mock_api.exchange.get_actuator_handle.return_value = 10

    manager = ActuatorManager(mock_api)
    manager.init_handles("dummy_state", ["HTGSETP_SCH_NO_OPTIMUM"])

    with pytest.raises(InvalidActuatorHandleError, match="was not registered"):
        manager.set_schedule_value("dummy_state", "UNKNOWN_SCH", 22.0)


def test_actuator_manager_set_zone_setpoints():
    mock_api = MagicMock()
    mock_api.exchange.get_actuator_handle.side_effect = lambda s, c, ctrl, name: (
        10 if name == "HTG" else 20
    )

    manager = ActuatorManager(mock_api)
    manager.init_handles("dummy_state", ["HTG", "CLG"])

    setpoints = ZoneSetpoints(heating_c=20.0, cooling_c=25.0)
    manager.set_zone_setpoints("dummy_state", "HTG", "CLG", setpoints)

    mock_api.exchange.set_actuator_value.assert_any_call("dummy_state", 10, 20.0)
    mock_api.exchange.set_actuator_value.assert_any_call("dummy_state", 20, 25.0)


def test_actuator_manager_incremental_init_handles():
    mock_api = MagicMock()
    mock_api.exchange.get_actuator_handle.side_effect = lambda s, c, ctrl, name: (
        101 if name == "SCH1" else (102 if name == "SCH2" else -1)
    )

    manager = ActuatorManager(mock_api)
    manager.init_handles("dummy_state", ["SCH1"])
    assert manager.handles == {"SCH1": 101}

    # Second call adds SCH2 incrementally
    manager.init_handles("dummy_state", ["SCH1", "SCH2"])
    assert manager.handles == {"SCH1": 101, "SCH2": 102}
