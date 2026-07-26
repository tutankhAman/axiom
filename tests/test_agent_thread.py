"""Unit tests for background AgentThread execution and event handling."""

import time

from agent.thread import AgentThread
from bridge.state_bridge import StateBridge
from sim.sensors import SimulationState


def test_agent_thread_lifecycle() -> None:
    bridge = StateBridge()
    agent = AgentThread(bridge)

    agent.start()
    assert agent.is_alive()

    agent.stop(timeout=1.0)
    assert not agent.is_alive()


def test_agent_thread_trigger_wakeup() -> None:
    bridge = StateBridge()
    agent = AgentThread(bridge)
    agent.start()

    try:
        state = SimulationState(
            sim_time_hours=2.0,
            outdoor_temp=25.0,
            hvac_power_w=1200.0,
        )
        bridge.update_state(state)
        bridge.trigger()

        # Wait briefly for thread to process event
        time.sleep(0.2)

        assert agent.trigger_count == 1
        assert len(agent.invocations) == 1
        assert agent.invocations[0].sim_time_hours == 2.0
    finally:
        agent.stop(timeout=1.0)
