"""Unit tests for deterministic PreFilter logic."""

from agent.prefilter import PreFilter
from sim.sensors import SimulationState, ZoneState


def make_state(sim_time_hours: float, pmv: float = 0.0) -> SimulationState:
    return SimulationState(
        sim_time_hours=sim_time_hours,
        outdoor_temp=20.0,
        hvac_power_w=1000.0,
        zones={"Core_ZN": ZoneState(zone_name="Core_ZN", mean_air_temp=22.0, pmv=pmv, ppd=5.0)},
    )


def test_prefilter_initial_trigger() -> None:
    prefilter = PreFilter(interval_hours=1.0)
    state = make_state(sim_time_hours=0.0, pmv=0.0)

    decision = prefilter.evaluate(state)
    assert decision.should_trigger is True
    assert "Initial trigger" in decision.reason
    assert prefilter.last_trigger_time == 0.0


def test_prefilter_no_trigger_within_interval_and_comfort() -> None:
    prefilter = PreFilter(interval_hours=1.0)
    prefilter.evaluate(make_state(sim_time_hours=0.0, pmv=0.0))

    # Evaluate at 0.5h with normal PMV
    state_0_5 = make_state(sim_time_hours=0.5, pmv=0.2)
    decision = prefilter.evaluate(state_0_5)

    assert decision.should_trigger is False
    assert prefilter.last_trigger_time == 0.0


def test_prefilter_trigger_on_interval_elapsed() -> None:
    prefilter = PreFilter(interval_hours=1.0)
    prefilter.evaluate(make_state(sim_time_hours=0.0, pmv=0.0))

    # Evaluate at 1.0h
    state_1_0 = make_state(sim_time_hours=1.0, pmv=0.1)
    decision = prefilter.evaluate(state_1_0)

    assert decision.should_trigger is True
    assert "Control interval elapsed" in decision.reason
    assert prefilter.last_trigger_time == 1.0


def test_prefilter_trigger_on_pmv_comfort_violation_high() -> None:
    prefilter = PreFilter(interval_hours=1.0, pmv_max=0.5)
    prefilter.evaluate(make_state(sim_time_hours=0.0, pmv=0.0))

    # At 0.2h, PMV spikes to 0.8 (too hot)
    state_hot = make_state(sim_time_hours=0.2, pmv=0.8)
    decision = prefilter.evaluate(state_hot)

    assert decision.should_trigger is True
    assert "outside comfort band" in decision.reason
    assert prefilter.last_trigger_time == 0.2


def test_prefilter_trigger_on_pmv_comfort_violation_low() -> None:
    prefilter = PreFilter(interval_hours=1.0, pmv_min=-0.5)
    prefilter.evaluate(make_state(sim_time_hours=0.0, pmv=0.0))

    # At 0.3h, PMV drops to -0.7 (too cold)
    state_cold = make_state(sim_time_hours=0.3, pmv=-0.7)
    decision = prefilter.evaluate(state_cold)

    assert decision.should_trigger is True
    assert "outside comfort band" in decision.reason
    assert prefilter.last_trigger_time == 0.3
