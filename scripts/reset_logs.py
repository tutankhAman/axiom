"""Reset simulation output logs and dashboard feeds for clean live testing."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_JSON = PROJECT_ROOT / "dashboard" / "public" / "live_data.json"
SRC_JSON = PROJECT_ROOT / "dashboard" / "src" / "dashboard_data.json"
OUTPUT_DIR = PROJECT_ROOT / "output" / "phase5_experiments"

READY_DATA = {
    "is_live": False,
    "status": "ready",
    "current_step": 0,
    "current_sim_time_hours": 0.0,
    "summary": {
        "baseline_kwh": 0.0,
        "closed_loop_kwh": 0.0,
        "pct_savings": 0.0,
        "comfort_compliance_pct_baseline": 100.0,
        "comfort_compliance_pct_closed_loop": 100.0,
    },
    "power_series": [],
    "pmv_series": [],
    "decision_log": [],
}


def reset() -> None:
    """Clear output files and write initial empty JSON feeds."""
    for json_file in [PUBLIC_JSON, SRC_JSON]:
        json_file.parent.mkdir(parents=True, exist_ok=True)
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(READY_DATA, f, indent=2)

    # Clean old CSV output if present
    comfort_csv = OUTPUT_DIR / "phase5_comfort_results.csv"
    if comfort_csv.exists():
        comfort_csv.unlink()

    print("Cleared all previous simulation logs and reset live dashboard feeds.")
    print("   -> dashboard/public/live_data.json: RESET")
    print("   -> dashboard/src/dashboard_data.json: RESET")
    print("   -> output/phase5_experiments/phase5_comfort_results.csv: CLEARED")


if __name__ == "__main__":
    reset()
