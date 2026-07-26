"""Main entrypoint for Phase 2 baseline simulation run and CSV export."""

import csv
import logging
import os
import sys

from sim import EnergyPlusDriver, SimulationState

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


def main() -> int:
    setup_logging()
    logger.info("Starting Phase 2 Baseline Simulation Run...")

    base_dir = os.path.dirname(os.path.abspath(__file__))
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


if __name__ == "__main__":
    sys.exit(main())
