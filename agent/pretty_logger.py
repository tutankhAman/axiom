"""Pretty console formatter for Axiom Eco-Loop Building Agent."""

# ANSI Color Codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"


def print_banner(mode_str: str, sync_str: str, days: float) -> None:
    """Print clean ASCII startup banner."""
    title = "🏢 AXIOM ECO-LOOP BUILDING AGENT — PHYSICAL AI POC"
    b_top = f"{CYAN}{BOLD}╔═══════════════════════════════════════════════════════════════╗{RESET}"
    b_mid = f"{CYAN}{BOLD}╠═══════════════════════════════════════════════════════════════╣{RESET}"
    b_bot = f"{CYAN}{BOLD}╚═══════════════════════════════════════════════════════════════╝{RESET}"
    c_b = f"{CYAN}{BOLD}"
    m_fmt = f"{CYAN}║ Mode: {c_b}{mode_str:<15}{RESET}{CYAN} | Exec: {c_b}{sync_str:<15}{RESET}{CYAN} ║{RESET}"  # noqa: E501
    d_fmt = f"{CYAN}║ Horizon: {c_b}{days:.1f} Days ({int(days * 24)}h){RESET}{CYAN:<40} ║{RESET}"  # noqa: E501
    print(f"\n{b_top}")
    print(f"{CYAN}{BOLD}║ {title:<61} ║{RESET}")
    print(f"{b_mid}")
    print(m_fmt)
    print(d_fmt)
    print(f"{b_bot}\n")


def print_timestep_card(
    sim_time_hours: float,
    outdoor_temp: float,
    mean_zone_temp: float,
    pmv: float,
    hvac_power_w: float,
    is_occupied: bool,
    is_peak: bool,
    cool_setpoint: float,
    heat_setpoint: float,
    trigger_source: str = "PREFILTER",
    reason: str = "",
) -> None:
    """Print structured, beautified card for simulation timestep events."""
    day = int(sim_time_hours / 24) + 1
    hour = int(sim_time_hours % 24)
    minute = int((sim_time_hours % 1) * 60)
    time_str = f"Day {day} - {hour:02d}:{minute:02d}"

    pricing_tag = f"{RED}{BOLD}[PEAK]{RESET}" if is_peak else f"{GREEN}[OFF-PEAK]{RESET}"
    occ_tag = f"{BLUE}[OCCUPIED]{RESET}" if is_occupied else f"{DIM}[UNOCCUPIED]{RESET}"

    if abs(pmv) <= 0.5:
        pmv_str = f"{GREEN}{pmv:+.2f} (ASHRAE-55 Compliant){RESET}"
    elif abs(pmv) <= 0.7:
        pmv_str = f"{YELLOW}{pmv:+.2f} (Slight Drift){RESET}"
    else:
        pmv_str = f"{RED}{pmv:+.2f} (Violation){RESET}"

    power_kw = hvac_power_w / 1000.0

    print(f"{MAGENTA}┌── 🕒 {BOLD}{time_str}{RESET} {occ_tag} {pricing_tag} ──┐{RESET}")
    print(f"│ Out: {outdoor_temp:.1f}°C | Zone: {mean_zone_temp:.1f}°C | Power: {power_kw:.2f}kW")
    print(f"│ 📊 PMV Status: {pmv_str}")

    if trigger_source == "LLM":
        cl_str = f"{GREEN}{cool_setpoint:.1f}°C{RESET}"
        ht_str = f"{RED}{heat_setpoint:.1f}°C{RESET}"
        print(f"│ 🤖 {BOLD}LLM DECISION:{RESET} Cool: {cl_str} | Heat: {ht_str}")
        if reason:
            print(f"│ 💡 {DIM}Reason:{RESET} {reason}")
    else:
        sp_fmt = f"Cool: {cool_setpoint:.1f}°C | Heat: {heat_setpoint:.1f}°C"
        print(f"│ 🛡️ {DIM}Rule Engine / ZOH:{RESET} {sp_fmt}")

    print(f"{MAGENTA}└───────────────────────────────────────────────────────────────┘{RESET}\n")


def print_summary_card(
    total_hours: float,
    total_triggers: int,
    baseline_kwh: float,
    agent_kwh: float,
    savings_pct: float,
    comfort_pct: float,
    csv_path: str,
) -> None:
    """Print clean summary performance card."""
    b_top = f"{GREEN}{BOLD}╔═══════════════════════════════════════════════════════════════╗{RESET}"
    b_mid = f"{GREEN}{BOLD}╠═══════════════════════════════════════════════════════════════╣{RESET}"
    b_bot = f"{GREEN}{BOLD}╚═══════════════════════════════════════════════════════════════╝{RESET}"
    dur_str = f"⏱️ Duration   : {BOLD}{total_hours:.1f} Hours ({total_hours / 24:.1f} Days){RESET}"
    print(f"\n{b_top}")
    print(f"{GREEN}{BOLD}║                 🎉 EXPERIMENT RUN COMPLETED                   ║{RESET}")
    print(f"{b_mid}")
    print(f"{GREEN}║ {dur_str}{GREEN:<27}║{RESET}")
    print(f"{GREEN}║ 🤖 LLM Calls  : {BOLD}{total_triggers} Triggers{RESET}{GREEN:<36}║{RESET}")
    print(f"{GREEN}║ ⚡ Baseline   : {BOLD}{baseline_kwh:.1f} kWh{RESET}{GREEN:<36}║{RESET}")
    print(f"{GREEN}║ 🔋 Axiom AI   : {BOLD}{agent_kwh:.1f} kWh{RESET}{GREEN:<36}║{RESET}")
    print(f"{GREEN}║ 💰 Savings    : {BOLD}{GREEN}{savings_pct:+.1f}%{RESET}{GREEN:<38}║{RESET}")
    print(f"{GREEN}║ 🧘 Comfort    : {BOLD}{comfort_pct:.1f}% ASHRAE-55{RESET}{GREEN:<26}║{RESET}")
    print(f"{GREEN}║ 📄 Export CSV : {BOLD}{csv_path:<36}{RESET}{GREEN}║{RESET}")
    print(f"{b_bot}\n")
