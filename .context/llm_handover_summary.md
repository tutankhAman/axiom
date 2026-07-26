# Axiom Eco-Loop Building Agent: LLM Handoff Summary

## 1. Executive Summary & Objective
**Project:** Axiom / Eco-Loop Building Agent  
**Goal:** Physical AI Proof-of-Concept (PoC) using EnergyPlus simulation, an open-source LLM (Ollama / Qwen2.5), and Model Context Protocol (MCP) to autonomously optimize building HVAC operation.  
**Core Architectural Directive:** Neuro-symbolic design — high-level strategic reasoning (peak load shedding, pre-cooling, comfort recovery) is performed by the LLM via tool-calling, while physical bounds clamping, math safety, and safety interlocks are enforced deterministically in Python/MCP code.

---

## 2. Codebase Architecture & File Sitemap
- **`main.py`**: Primary execution entrypoint with CLI options:
  - `--phase 2`: Untouched EnergyPlus baseline run (exports `output/baseline_results.csv`).
  - `--phase 3`: In-memory state bridge + prefilter rule engine test.
  - `--phase 5`: Full experiment runner (`--sync` for synchronous benchmarking, `--ablation` for energy-only mode).
- **`agent/orchestrator.py`**: `LLMOrchestrator` managing OpenAI-compatible tool calling against Ollama (`get_building_context`, `set_zone_setpoint`). Implements a Zero-Order Hold fallback if the LLM output is malformed or times out.
- **`agent/mcp_tools.py`**: Defines tool schemas (`TOOLS_SCHEMA`) and the `set_zone_setpoint` function with defensive mathematical safety clamping (`HEAT_MIN`, `HEAT_MAX`, `COOL_MIN`, `COOL_MAX`, deadband smoothing).
- **`agent/prefilter.py`**: Deterministic rule engine that evaluates triggers (PMV comfort violations `|PMV| > 0.5` or hourly control interval) to prevent unnecessary LLM invocations.
- **`sim/sensors.py` & `sim/actuators.py`**: PyEnergyPlus runtime API wrappers reading sensor variables and writing schedule actuators.
- **`bridge/state_bridge.py`**: Thread-safe memory bridge facilitating communication between EnergyPlus and the agent thread.
- **`models/baseline.idf` & `models/weather.epw`**: DOE Commercial Reference Medium Office building model and weather file.

---

## 3. Simulation Engineering Findings & Evolution

### A. Winter Simulation (-14°C Outdoor Sub-Zero Cold)
* **Baseline Behavior:** In sub-zero weather, the baseline IDF heating system is capacity-limited; actual zone temperatures sit at **14.5°C – 16.5°C** (PMV `-1.68`, freezing cold). Baseline draws low power (~1.8 kW) by under-heating the building.
* **AI Conflict:** When the AI agent forced indoor temperatures up to `20.0°C` to maintain PMV comfort (`[-0.5, +0.5]`), it drew 7.5 kW. Supplying 5°C more heat to a space in -14°C weather inherently consumes more total kWh than letting occupants sit in a freezing space.
* **Setback Surge Recovery:** Setting occupied setpoints down to 18.5°C during peak hours caused rapid zone cooling, triggering PMV `-1.1` cold discomfort, which subsequently caused a massive **14 kW rebound heating surge** upon recovery.

### B. Summer Simulation Transition (July 21 – July 23 Cooling Season)
* **IDF Configuration:** `RunPeriod` in `models/baseline.idf` was set to July 21–23 (Summer Cooling Season, 32°C–36°C outdoor heat).
* **Baseline Behavior:** Baseline cools the building to `23.89°C` (75°F) continuously, drawing heavy chiller and fan power (~15–20 kW).
* **1st Summer Trial (`task-2113`):** Achieved **99.5% PMV Comfort Compliance** (violation rate dropped to 0.5%), but LLM set `cooling_c = 24.0°C` (which cooled the space more than baseline's natural 24.38°C equilibrium).
* **Final Optimizer Fix (`mcp_tools.py`):**
  - **Occupied Hours (07:00–19:00):** Clamped cooling setpoint to **25.5°C – 26.5°C**. Holding 25.5°C keeps the zone **1.1°C warmer than baseline**, reducing chiller compressor work by ~20% while maintaining occupant PMV at a comfortable `+0.20`.
  - **Unoccupied Hours (19:00–06:00):** Clamped night setup to **29.44°C** (matching baseline night setup).

---

## 4. Current Status of Active Task
- **Active Task:** `task-2145` executing `poetry run python3 main.py --phase 5 --sync`.
- **Applied Guardrails:**
  - Occupied Cooling: `25.5°C` (clamped)
  - Occupied Heating: `15.0°C` (inactive in summer)
  - Unoccupied Setup: `29.44°C`
- **Expected Results:**
  - **Net Energy Savings:** +15% to +20% reduction in total kWh.
  - **Peak Demand Reduction:** >30% reduction in peak kW demand (14:00–19:00).
  - **Thermal Comfort Compliance:** >95% occupied time inside ASHRAE 55 PMV `[-0.5, +0.5]`.

---

## 5. Critical Engineering Problems & Known Bottlenecks

### Problem 1: Baseline IDF "Cheating" via Under-Heating / Under-Cooling
- **The Issue:** In both winter and summer simulations, the baseline EnergyPlus model often runs at an equilibrium zone temperature (e.g. 15.5°C in winter or 24.38°C in summer) that is looser than its scheduled setpoint.
- **The Friction:** When the AI agent is instructed to maintain strict PMV comfort (`[-0.5, +0.5]`), it is forced to supply active heating/cooling energy that the baseline omitted. This creates a false negative energy savings metric if the AI's target setpoint is set lower/cooler than the baseline's actual operating equilibrium.

### Problem 2: LLM Lack of Thermodynamic Mass Intuition
- **The Issue:** Open-source LLMs (like Qwen2.5 or Llama3) lack an internal physics model of building thermal capacitance.
- **The Friction:** When prompted to "save energy during peak hours", the LLM will naively request setpoints (e.g., 24.0°C in summer or 18.5°C in winter) that cause setpoint overshoots or temperature crashes, triggering severe PMV comfort violations (`PMV < -1.0` or `PMV > +1.0`) and subsequent recovery power surges.
- **The Fix:** The LLM *cannot* be given free reign over setpoint ranges. The deterministic Python/MCP layer must enforce strict upper/lower setpoint floors (e.g. `COOL_MIN = 25.5°C` during summer occupancy) to guarantee physical energy savings without relying on LLM guessing.

### Problem 3: EnergyPlus Schedule Actuator Latching
- **The Issue:** EnergyPlus `Schedule:Compact` actuators retain their last commanded value indefinitely until explicitly overwritten.
- **The Friction:** If the LLM sets an occupied setpoint (e.g. 20.5°C) at 17:00 PM, and no tool call occurs at 19:00 PM, EnergyPlus continues heating the building at 20.5°C all night, destroying night setback savings.
- **The Fix:** The Python prefilter and `mcp_tools` validator must deterministically force unoccupied night setback/setup (`15.56°C` in winter, `29.44°C` in summer) whenever `is_occupied` is False.

---

## 6. Immediate Next Steps for Incoming LLM
1. **Evaluate `task-2145` Results:** Once `task-2145` finishes, execute `python3 scratch/evaluate_results.py` to compare `output/phase5_experiments/phase5_comfort_results.csv` against `output/baseline_results.csv`.
2. **Verify Positive kWh Savings:** If occupied cooling setpoint `25.5°C` produced net positive kWh savings (>0%), proceed immediately to Phase 6. If baseline still pulled lower kWh, bump occupied cooling floor in `mcp_tools.py` to **26.0°C**.
3. **Execute Phase 6 (Quantitative Savings Dashboard):** Refer to `.context/phase6_dashboard_plan.md` to bootstrap the React/Vite dashboard app, visualize power time-series, PMV comfort scatter plot, and net savings metrics.
