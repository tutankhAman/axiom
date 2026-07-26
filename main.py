"""Main entrypoint for baseline and Phase 3 bridged simulation runs."""

import argparse
import csv
import logging
import os
import sys
from typing import Any

from agent import AgentThread, PreFilter
from bridge import StateBridge
from sim import ActuatorManager, EnergyPlusDriver, SimulationState

logger = logging.getLogger("main")


def setup_logging() -> None:
    """Configure clean console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def save_history_to_csv(history: list[SimulationState], csv_path: str) -> None:
    """Export simulation state history to a CSV file."""
    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "sim_time_hours",
                "outdoor_temp_c",
                "hvac_power_w",
                "zone_name",
                "mean_air_temp_c",
                "pmv",
                "ppd",
            ]
        )
        for state in history:
            for zone_name, zone_data in state.zones.items():
                writer.writerow(
                    [
                        f"{state.sim_time_hours:.4f}",
                        f"{state.outdoor_temp:.2f}",
                        f"{state.hvac_power_w:.2f}",
                        zone_name,
                        f"{zone_data.mean_air_temp:.2f}",
                        f"{zone_data.pmv:.4f}",
                        f"{zone_data.ppd:.4f}",
                    ]
                )
    logger.info("Saved %d state snapshots to CSV: %s", len(history), csv_path)


def run_phase3(base_dir: str | None = None, output_dir: str | None = None) -> tuple[int, int]:
    """Run Phase 3 in-memory state bridge + pre-filter agent simulation."""
    logger.info("Starting Phase 3 Bridged Simulation Run (State Bridge + Pre-filter)...")

    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    if output_dir is None:
        output_dir = os.path.join(base_dir, "output", "phase3_bridged_run")

    bridge = StateBridge()
    prefilter = PreFilter(interval_hours=1.0)
    agent_thread = AgentThread(bridge)
    agent_thread.start()

    def on_timestep(sim_state: SimulationState) -> None:
        bridge.update_state(sim_state)
        decision = prefilter.evaluate(sim_state)
        if decision.should_trigger:
            bridge.trigger()

    def on_actuate(state: Any, actuator_manager: ActuatorManager) -> None:
        commands = bridge.get_actuation_commands()
        for sched_name, val in commands.items():
            actuator_manager.set_schedule_value(state, sched_name, val)

    driver = EnergyPlusDriver(
        idf_path=os.path.join(base_dir, "models", "baseline.idf"),
        epw_path=os.path.join(base_dir, "models", "weather.epw"),
        output_dir=output_dir,
        on_timestep=on_timestep,
        on_actuate=on_actuate,
    )

    try:
        exit_code = driver.run()
    finally:
        agent_thread.stop()

    if exit_code == 0:
        csv_path = os.path.join(output_dir, "phase3_results.csv")
        save_history_to_csv(driver.history, csv_path)
        logger.info(
            "Phase 3 bridged run finished successfully! Agent thread was triggered %d times.",
            agent_thread.trigger_count,
        )
    else:
        logger.error("Phase 3 bridged run failed with exit code: %d", exit_code)

    return exit_code, agent_thread.trigger_count


def run_baseline(base_dir: str) -> int:
    """Run Phase 2 untouched baseline simulation."""
    logger.info("Starting Phase 2 Baseline Simulation Run...")

    driver = EnergyPlusDriver(
        idf_path=os.path.join(base_dir, "models", "baseline.idf"),
        epw_path=os.path.join(base_dir, "models", "weather.epw"),
        output_dir=os.path.join(base_dir, "output", "phase2_baseline_run"),
    )

    exit_code = driver.run()

    if exit_code == 0:
        csv_path = os.path.join(base_dir, "output", "baseline_results.csv")
        save_history_to_csv(driver.history, csv_path)
        logger.info(
            "Phase 2 baseline run completed successfully! Saved baseline results to %s",
            csv_path,
        )
    else:
        logger.error("Phase 2 baseline run failed with exit code: %d", exit_code)

    return exit_code


def main() -> int:
    setup_logging()
    parser = argparse.ArgumentParser(description="Eco-Loop Simulation Runner")
    parser.add_argument(
        "--phase",
        choices=["2", "3"],
        default="3",
        help="Phase run mode: 2 (baseline), 3 (bridged + prefilter, default)",
    )
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))

    if args.phase == "3":
        exit_code, _ = run_phase3(base_dir)
        return exit_code
    else:
        return run_baseline(base_dir)


if __name__ == "__main__":
    sys.exit(main())
