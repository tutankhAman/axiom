"""Unit tests for in-memory StateBridge concurrency and thread-safety."""

import threading

from bridge.state_bridge import StateBridge
from sim.sensors import SimulationState, ZoneState


def test_state_bridge_initialization() -> None:
    bridge = StateBridge()
    assert bridge.get_latest_state() is None
    assert bridge.get_actuation_commands() == {}
    assert not bridge.trigger_event.is_set()


def test_state_bridge_update_and_get_state() -> None:
    bridge = StateBridge()
    state = SimulationState(
        sim_time_hours=1.5,
        outdoor_temp=22.0,
        hvac_power_w=1500.0,
        zones={"Core_ZN": ZoneState(zone_name="Core_ZN", mean_air_temp=21.5, pmv=0.1, ppd=5.0)},
    )

    bridge.update_state(state)
    retrieved = bridge.get_latest_state()

    assert retrieved is not None
    assert retrieved.sim_time_hours == 1.5
    assert retrieved.zones["Core_ZN"].mean_air_temp == 21.5


def test_state_bridge_actuation_commands() -> None:
    bridge = StateBridge()
    commands = {"HTGSETP_SCH_NO_OPTIMUM": 20.0, "CLGSETP_SCH_NO_OPTIMUM": 24.0}

    bridge.set_actuation_commands(commands)
    retrieved = bridge.get_actuation_commands()

    assert retrieved == commands
    # Ensure returned dictionary is a copy
    retrieved["HTGSETP_SCH_NO_OPTIMUM"] = 18.0
    assert bridge.get_actuation_commands()["HTGSETP_SCH_NO_OPTIMUM"] == 20.0


def test_state_bridge_concurrent_access() -> None:
    bridge = StateBridge()
    errors: list[Exception] = []

    def writer_thread() -> None:
        try:
            for i in range(100):
                state = SimulationState(
                    sim_time_hours=float(i),
                    outdoor_temp=20.0 + i * 0.1,
                    hvac_power_w=1000.0,
                )
                bridge.update_state(state)
                bridge.set_actuation_commands({"HTGSETP": 20.0 + (i % 5)})
        except Exception as e:
            errors.append(e)

    def reader_thread() -> None:
        try:
            for _ in range(100):
                _ = bridge.get_latest_state()
                _ = bridge.get_actuation_commands()
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=writer_thread),
        threading.Thread(target=reader_thread),
        threading.Thread(target=writer_thread),
        threading.Thread(target=reader_thread),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Errors occurred during concurrent state bridge access: {errors}"
