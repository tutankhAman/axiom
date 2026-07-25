"""Main entrypoint for Phase 1 read-only simulation loop."""

import logging
import sys

from sim.driver import EnergyPlusDriver


def setup_logging() -> None:
    """Configure clean console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main() -> int:
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("Starting Phase 1 Read-Only Simulation Loop...")

    driver = EnergyPlusDriver(
        idf_path="models/baseline.idf",
        epw_path="models/weather.epw",
        output_dir="output/phase1_run",
    )

    exit_code = driver.run()

    if exit_code == 0:
        logger.info(
            "Phase 1 simulation completed successfully! Collected %d timesteps of sensor data.",
            len(driver.history),
        )
        if driver.history:
            sample_state = driver.history[0]
            logger.info("Sample Timestep State: %s", sample_state)
    else:
        logger.error("Simulation failed with exit code: %d", exit_code)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
