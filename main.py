"""Main entrypoint for baseline and Phase 5 simulation runs."""

import argparse
import csv
import logging
import os
import sys
from typing import Any

from agent import AgentThread, PreFilter
from agent.live_exporter import LiveDashboardExporter
from agent.pretty_logger import (
    print_banner,
    print_summary_card,
    print_timestep_card,
)
from bridge import StateBridge
from sim import ActuatorManager, EnergyPlusDriver, SimulationState
from sim.sensors import ZoneState

logger = logging.getLogger("main")


def setup_logging() -> None:
    """Configure clean console logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def update_idf_duration(idf_path: str, days: int = 4) -> None:
    """Update RunPeriod in baseline.idf to requested duration in days."""
    if not os.path.exists(idf_path):
        return

    begin_month, begin_day = 7, 21
    end_day = begin_day + days - 1
    end_month = begin_month
    if end_day > 31:
        end_day -= 31
        end_month += 1

    with open(idf_path, encoding="utf-8") as f:
        lines = f.readlines()

    in_run_period = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("RunPeriod,"):
            in_run_period = True
            continue
        if not in_run_period:
            continue

        indent = line[: len(line) - len(line.lstrip())]

        if "!- Begin Day of Month" in line:
            lines[i] = f"{indent}{begin_day},                       !- Begin Day of Month\n"
        elif "!- End Month" in stripped:
            lines[i] = f"{indent}{end_month},                        !- End Month\n"
        elif "!- End Day of Month" in stripped:
            lines[i] = f"{indent}{end_day},                       !- End Day of Month\n"
            break

    with open(idf_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


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


def load_baseline_history(csv_path: str) -> list[SimulationState]:
    """Load cached baseline simulation states if available."""
    if not os.path.exists(csv_path):
        return []
    history: list[SimulationState] = []
    try:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            cur_time: float | None = None
            cur_state: SimulationState | None = None
            for row in reader:
                time_h = float(row["sim_time_hours"])
                power_w = float(row["hvac_power_w"])
                pmv_val = float(row["pmv"])
                # Skip Sizing Period shadow rows that skew timestamp alignment
                if power_w == 0.0 and pmv_val == 0.0 and time_h < 4000.0:
                    continue
                if cur_time != time_h:
                    if cur_state is not None:
                        history.append(cur_state)
                    cur_time = time_h
                    cur_state = SimulationState(
                        sim_time_hours=time_h,
                        outdoor_temp=float(row["outdoor_temp_c"]),
                        hvac_power_w=power_w,
                    )
                if cur_state is not None:
                    z_name = row["zone_name"]
                    cur_state.zones[z_name] = ZoneState(
                        zone_name=z_name,
                        mean_air_temp=float(row["mean_air_temp_c"]),
                        pmv=pmv_val,
                        ppd=float(row["ppd"]),
                    )
            if cur_state is not None:
                history.append(cur_state)
    except Exception as e:
        logger.warning("Could not load baseline CSV history: %s", e)
    return history


def run_phase3(base_dir: str | None = None, output_dir: str | None = None) -> tuple[int, int]:
    """Run Phase 3 in-memory state bridge + pre-filter agent simulation."""
    logger.info("Starting Phase 3 Bridged Simulation Run...")
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
        if decision.setback_command:
            current_cmds = bridge.get_actuation_commands()
            current_cmds["HTGSETP_SCH_NO_OPTIMUM"] = decision.setback_command["heat"]
            current_cmds["CLGSETP_SCH_NO_OPTIMUM"] = decision.setback_command["cool"]
            current_cmds["HTGSETP_SCH_NO_OPTIMUM_w_SB"] = decision.setback_command["heat"]
            current_cmds["CLGSETP_SCH_NO_OPTIMUM_w_SB"] = decision.setback_command["cool"]
            bridge.set_actuation_commands(current_cmds)
        elif decision.should_trigger:
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
    return exit_code, agent_thread.trigger_count


def run_phase5(
    base_dir: str | None = None,
    output_dir: str | None = None,
    sync: bool = False,
    ablation: bool = False,
    days: int = 4,
) -> tuple[int, int]:
    """Run Phase 5 experiment variants with live dashboard streaming & pretty logging."""
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    idf_path = os.path.join(base_dir, "models", "baseline.idf")
    update_idf_duration(idf_path, days=days)

    mode_str = "Ablation (Energy-Only)" if ablation else "Comfort-Constrained"
    sync_str = "Synchronous (Benchmarking)" if sync else "Asynchronous (Demo)"
    print_banner(mode_str, sync_str, days=float(days))

    if output_dir is None:
        output_dir = os.path.join(base_dir, "output", "phase5_experiments")

    baseline_csv = os.path.join(base_dir, "output", "baseline_results.csv")
    baseline_history = load_baseline_history(baseline_csv)

    bridge = StateBridge()
    prefilter = PreFilter(interval_hours=1.0, min_cooldown_hours=0.5)
    exporter = LiveDashboardExporter(baseline_history=baseline_history)
    trigger_count = 0

    if sync:
        from agent.orchestrator import LLMOrchestrator

        orchestrator = LLMOrchestrator(bridge=bridge, ablation_mode=ablation)
        agent_thread = None
    else:
        orchestrator = None
        agent_thread = AgentThread(bridge, ablation_mode=ablation)
        agent_thread.start()

    running_history: list[SimulationState] = []

    def on_timestep(sim_state: SimulationState) -> None:
        nonlocal trigger_count
        running_history.append(sim_state)
        bridge.update_state(sim_state)
        decision = prefilter.evaluate(sim_state)

        last_cmds = bridge.get_actuation_commands()
        cool_sp = last_cmds.get("CLGSETP_SCH_NO_OPTIMUM", 26.5)
        heat_sp = last_cmds.get("HTGSETP_SCH_NO_OPTIMUM", 15.0)

        source = "PREFILTER"
        reason = ""

        if decision.setback_command:
            current_cmds = bridge.get_actuation_commands()
            cool_sp = decision.setback_command["cool"]
            heat_sp = decision.setback_command["heat"]
            current_cmds["HTGSETP_SCH_NO_OPTIMUM"] = heat_sp
            current_cmds["CLGSETP_SCH_NO_OPTIMUM"] = cool_sp
            current_cmds["HTGSETP_SCH_NO_OPTIMUM_w_SB"] = heat_sp
            current_cmds["CLGSETP_SCH_NO_OPTIMUM_w_SB"] = cool_sp
            reason = "Night setup / Unoccupied setback applied deterministically."
            bridge.set_actuation_commands(current_cmds, reason=reason)
            source = "SETBACK"

        elif decision.should_trigger:
            trigger_count += 1
            source = "LLM"
            if sync and orchestrator:
                orchestrator.evaluate_and_act()
                new_cmds = bridge.get_actuation_commands()
                cool_sp = new_cmds.get("CLGSETP_SCH_NO_OPTIMUM", cool_sp)
                heat_sp = new_cmds.get("HTGSETP_SCH_NO_OPTIMUM", heat_sp)
                reason = (
                    bridge.get_last_reason()
                    or "LLM evaluated building state and selected optimal setpoints."
                )
            else:
                bridge.trigger()
                reason = bridge.get_last_reason() or "Agent thread triggered asynchronously."

        zone_temps = (
            [z.mean_air_temp for z in sim_state.zones.values()] if sim_state.zones else [25.0]
        )
        mean_zone_temp = sum(zone_temps) / len(zone_temps)
        pmvs = [z.pmv for z in sim_state.zones.values()] if sim_state.zones else [0.0]
        mean_pmv = sum(pmvs) / len(pmvs)

        hour = int(sim_state.sim_time_hours % 24)
        is_peak = 14 <= hour < 19

        if source in ("LLM", "SETBACK") or (int(sim_state.sim_time_hours * 4) % 4 == 0):
            exporter.record_decision(
                sim_time_hours=sim_state.sim_time_hours,
                heating_c=heat_sp,
                cooling_c=cool_sp,
                reason=reason or "Periodic telemetry snapshot",
                baseline_pmv=0.0,
                agent_pmv=mean_pmv,
            )

        if source == "LLM" or (int(sim_state.sim_time_hours * 4) % 8 == 0):
            print_timestep_card(
                sim_time_hours=sim_state.sim_time_hours,
                outdoor_temp=sim_state.outdoor_temp,
                mean_zone_temp=mean_zone_temp,
                pmv=mean_pmv,
                hvac_power_w=sim_state.hvac_power_w,
                is_occupied=sim_state.is_occupied,
                is_peak=is_peak,
                cool_setpoint=cool_sp,
                heat_setpoint=heat_sp,
                trigger_source=source,
                reason=reason,
            )

        exporter.export_snapshot(
            agent_history=running_history,
            is_live=True,
            status="simulating",
        )

    def on_actuate(state: Any, actuator_manager: ActuatorManager) -> None:
        commands = bridge.get_actuation_commands()
        for sched_name, val in commands.items():
            actuator_manager.set_schedule_value(state, sched_name, val)

    driver = EnergyPlusDriver(
        idf_path=idf_path,
        epw_path=os.path.join(base_dir, "models", "weather.epw"),
        output_dir=output_dir,
        on_timestep=on_timestep,
        on_actuate=on_actuate,
    )

    try:
        exit_code = driver.run()
    finally:
        if agent_thread:
            agent_thread.stop()
        exporter.export_snapshot(agent_history=driver.history, is_live=False, status="completed")

    final_triggers = trigger_count if sync else (agent_thread.trigger_count if agent_thread else 0)

    if exit_code == 0:
        filename = "phase5_ablation_results.csv" if ablation else "phase5_comfort_results.csv"
        csv_path = os.path.join(output_dir, filename)
        save_history_to_csv(driver.history, csv_path)

        agent_kwh = sum(s.hvac_power_w * 0.25 for s in driver.history) / 1000.0

        baseline_kwh: float | None = None
        if baseline_history:
            # Align by sim_time_hours instead of length slice
            b_by_time = {round(b.sim_time_hours, 2): b for b in baseline_history}
            baseline_kwh = 0.0
            matched = 0
            for s in driver.history:
                b = b_by_time.get(round(s.sim_time_hours, 2))
                if b:
                    baseline_kwh += b.hvac_power_w * 0.25 / 1000.0
                    matched += 1
            if matched == 0:
                baseline_kwh = None

        savings_pct = (
            ((baseline_kwh - agent_kwh) / baseline_kwh * 100.0)
            if baseline_kwh is not None and baseline_kwh > 0
            else None
        )

        occ_pmvs = []
        for s in driver.history:
            if 7 <= (s.sim_time_hours % 24) < 19:
                z_pmvs = [z.pmv for z in s.zones.values()] if s.zones else [0.0]
                occ_pmvs.append(sum(z_pmvs) / len(z_pmvs))

        comp_count = sum(1 for p in occ_pmvs if -0.5 <= p <= 0.5)
        comfort_pct = (comp_count / len(occ_pmvs) * 100.0) if occ_pmvs else None

        print_summary_card(
            total_hours=driver.history[-1].sim_time_hours if driver.history else days * 24.0,
            total_triggers=final_triggers,
            baseline_kwh=baseline_kwh,
            agent_kwh=agent_kwh,
            savings_pct=savings_pct,
            comfort_pct=comfort_pct,
            csv_path=csv_path,
        )
    else:
        logger.error("Phase 5 run failed with exit code: %d", exit_code)

    return exit_code, final_triggers


def run_baseline(base_dir: str, days: int = 4) -> int:
    """Run Phase 2 untouched baseline simulation."""
    logger.info("Starting Phase 2 Baseline Simulation Run for %d days...", days)
    idf_path = os.path.join(base_dir, "models", "baseline.idf")
    update_idf_duration(idf_path, days=days)
    driver = EnergyPlusDriver(
        idf_path=idf_path,
        epw_path=os.path.join(base_dir, "models", "weather.epw"),
        output_dir=os.path.join(base_dir, "output", "phase2_baseline_run"),
    )
    exit_code = driver.run()
    if exit_code == 0:
        csv_path = os.path.join(base_dir, "output", "baseline_results.csv")
        save_history_to_csv(driver.history, csv_path)
        logger.info("Baseline run finished! Saved to %s", csv_path)
    return exit_code


def main() -> int:
    setup_logging()
    parser = argparse.ArgumentParser(description="Axiom Physical AI Building Agent")
    parser.add_argument(
        "--phase",
        choices=["2", "3", "5"],
        default="5",
        help="Phase run mode: 2 (baseline), 3 (bridged demo), 5 (closed-loop experiments)",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Run LLM evaluation synchronously (benchmarking mode)",
    )
    parser.add_argument(
        "--ablation",
        action="store_true",
        help="Run in energy-only ablation mode (ignores PMV constraints)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=4,
        help="Simulation duration in days (default: 4 days)",
    )
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))

    if args.phase == "5":
        exit_code, _ = run_phase5(
            base_dir,
            sync=args.sync,
            ablation=args.ablation,
            days=args.days,
        )
        return exit_code
    elif args.phase == "3":
        exit_code, _ = run_phase3(base_dir)
        return exit_code
    else:
        return run_baseline(base_dir, days=args.days)


if __name__ == "__main__":
    sys.exit(main())
