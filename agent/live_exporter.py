"""Live JSON exporter streaming real-time simulation metrics to React dashboard."""

import json
import logging
import os
from typing import Any

from sim.sensors import SimulationState

logger = logging.getLogger(__name__)

# Absolute paths for dashboard live feeds
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_LIVE_JSON = os.path.join(BASE_DIR, "dashboard", "public", "live_data.json")
SRC_DATA_JSON = os.path.join(BASE_DIR, "dashboard", "src", "dashboard_data.json")


class LiveDashboardExporter:
    """Manages real-time live data export for the React dashboard."""

    def __init__(self, baseline_history: list[SimulationState] | None = None):
        self.baseline_history = baseline_history or []
        self.decision_logs: list[dict[str, Any]] = []

        # Ensure directories exist
        os.makedirs(os.path.dirname(PUBLIC_LIVE_JSON), exist_ok=True)
        os.makedirs(os.path.dirname(SRC_DATA_JSON), exist_ok=True)

    def record_decision(
        self,
        sim_time_hours: float,
        heating_c: float,
        cooling_c: float,
        reason: str,
        baseline_pmv: float,
        agent_pmv: float,
    ) -> None:
        """Record an LLM or prefilter control decision without duplicate logs."""
        day = int(sim_time_hours / 24) + 1
        hour_of_day = int(sim_time_hours % 24)

        # Deduplicate identical consecutive setback / periodic logs
        if self.decision_logs:
            last = self.decision_logs[-1]
            if (
                last["heating_c"] == round(heating_c, 1)
                and last["cooling_c"] == round(cooling_c, 1)
                and last["reason"] == reason
            ):
                return

        entry = {
            "hour": round(sim_time_hours, 2),
            "day": day,
            "hour_of_day": hour_of_day,
            "zone": "ALL_ZONES",
            "heating_c": round(heating_c, 1),
            "cooling_c": round(cooling_c, 1),
            "reason": reason,
            "baseline_pmv": round(baseline_pmv, 3),
            "agent_pmv": round(agent_pmv, 3),
        }
        self.decision_logs.append(entry)

    def export_snapshot(
        self,
        agent_history: list[SimulationState],
        is_live: bool = True,
        status: str = "simulating",
    ) -> None:
        """Calculate current metrics and write live_data.json starting strictly at hour 0.0."""
        if not agent_history:
            return

        power_series = []
        pmv_series = []

        total_agent_kwh = 0.0
        total_baseline_kwh = 0.0

        compliant_occupied = 0
        total_occupied = 0

        b_compliant_occupied = 0
        b_total_occupied = 0

        first_h = agent_history[0].sim_time_hours if agent_history else 0.0

        # Create map of baseline states by timestamp for exact lookup
        b_map = {round(b.sim_time_hours, 2): b for b in self.baseline_history}

        for state in agent_history:
            h_rel = round(state.sim_time_hours - first_h, 2)
            if h_rel < 0:
                continue

            agent_p = state.hvac_power_w
            zone_pmvs = [z.pmv for z in state.zones.values()] if state.zones else [0.0]
            agent_pmv = sum(zone_pmvs) / len(zone_pmvs) if zone_pmvs else 0.0

            # Match baseline timestamp
            b_state = b_map.get(round(state.sim_time_hours, 2))
            if b_state:
                b_p = b_state.hvac_power_w
                b_zone_pmvs = [z.pmv for z in b_state.zones.values()] if b_state.zones else [0.0]
                b_pmv = sum(b_zone_pmvs) / len(b_zone_pmvs) if b_zone_pmvs else 0.0
            else:
                # No matching baseline sample — skip this timestep for baseline totals
                b_p = 0.0
                b_pmv = 0.0

            # Integrate kWh (15-min = 0.25h timesteps)
            total_agent_kwh += (agent_p * 0.25) / 1000.0
            if b_state:
                total_baseline_kwh += (b_p * 0.25) / 1000.0

            # Occupied comfort (evaluated ONLY during occupied hours, excluding weekends)
            if state.is_occupied:
                total_occupied += 1
                if -0.5 <= agent_pmv <= 0.5:
                    compliant_occupied += 1

            if b_state and state.is_occupied:
                b_total_occupied += 1
                if -0.5 <= b_pmv <= 0.5:
                    b_compliant_occupied += 1

            power_series.append(
                {
                    "hour": h_rel,
                    "baseline_w": round(b_p, 1),
                    "agent_w": round(agent_p, 1),
                }
            )

            pmv_series.append(
                {
                    "hour": h_rel,
                    "baseline_pmv": round(b_pmv, 3),
                    "agent_pmv": round(agent_pmv, 3),
                }
            )

        pct_savings = (
            ((total_baseline_kwh - total_agent_kwh) / total_baseline_kwh * 100.0)
            if total_baseline_kwh > 0
            else 0.0
        )
        comfort_pct = (compliant_occupied / total_occupied * 100.0) if total_occupied > 0 else 100.0
        b_comfort_pct = (
            (b_compliant_occupied / b_total_occupied * 100.0) if b_total_occupied > 0 else None
        )

        summary = {
            "baseline_kwh": round(total_baseline_kwh, 1),
            "closed_loop_kwh": round(total_agent_kwh, 1),
            "pct_savings": round(pct_savings, 1),
            "comfort_compliance_pct_closed_loop": round(comfort_pct, 1),
            "comfort_compliance_pct_baseline": (
                round(b_comfort_pct, 1) if b_comfort_pct is not None else None
            ),
        }

        data = {
            "is_live": is_live,
            "status": status,
            "current_step": len(agent_history),
            "current_sim_time_hours": round(agent_history[-1].sim_time_hours, 2),
            "summary": summary,
            "power_series": power_series,
            "pmv_series": pmv_series,
            "decision_log": self.decision_logs,
        }

        # Atomic write: serialize to temp file, then os.replace to avoid partial reads
        for path in [PUBLIC_LIVE_JSON, SRC_DATA_JSON]:
            try:
                tmp_path = path + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                os.replace(tmp_path, path)
            except Exception as e:
                logger.warning("Failed writing live dashboard data to %s: %s", path, e)
