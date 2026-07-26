# Axiom — Closed-Loop Physical AI Building Agent



https://github.com/user-attachments/assets/e892ea5f-ece7-497b-965c-d928a4aa2001



Axiom is a Physical AI Proof-of-Concept (PoC) that automates commercial building HVAC operation. It pairs the **EnergyPlus** physics simulation engine with an open-source Large Language Model (**Qwen 2.5**) via the **Model Context Protocol (MCP)** to execute autonomous, closed-loop thermal setpoint optimization.

Axiom utilizes a **neuro-symbolic design**: strategic reasoning (pre-cooling, peak load shedding, setback recovery) is managed by the LLM via tool-calling, while physical safety bounds, deadband smoothing, and emergency interlocks are enforced deterministically in Python.

---

## Performance Metrics

Evaluation results against the DOE Commercial Reference Medium Office baseline over a 3-day summer peak cooling period (July 21-24):

| Metric | Baseline | Axiom AI Agent | Impact |
| :--- | :---: | :---: | :---: |
| **Total Energy Consumption** | 117.7 kWh | 88.8 kWh | **24.6% kWh Reduction** |
| **Thermal Comfort Compliance** | 79.2% | 100.0% | **+20.8% ASHRAE-55 Compliance** |
| **LLM Tool Calls (over 3 days)** | N/A | 30 calls | **94% fewer than tick-by-tick** |
| **LLM Execution Latency Fallback** | N/A | Zero-Order Hold | **0 simulation crashes** |

*Thermal comfort compliance is evaluated using Fanger's Predicted Mean Vote (PMV) strictly within the ASHRAE-55 acceptable range `[-0.5, +0.5]` during occupied hours. 288 total simulation timesteps at 15-minute resolution.*

---

## Architecture Overview

```
+-------------------------------------------------------------------+
|                        PyEnergyPlus Engine                        |
|   Reads: Zone Temperatures, Outdoor Drybulb, HVAC Power, PMV      |
|   Writes: Schedule Actuators (CLGSETP_SCH, HTGSETP_SCH)           |
+-------------------------------------------------------------------+
                                 ^ |
                 State Updates   | | Actuation Commands
                                 | v
+-------------------------------------------------------------------+
|                     Thread-Safe StateBridge                       |
+-------------------------------------------------------------------+
                                 ^ |
                Filtered Trigger | | Setpoint Decisions
                                 | v
+-------------------------------------------------------------------+
|                      Deterministic PreFilter                      |
|       Triggers on |PMV| > 0.5 or scheduled 1-hour interval        |
+-------------------------------------------------------------------+
                                 ^ |
                    MCP Schema   | | JSON Function Calls
                                 | v
+-------------------------------------------------------------------+
|                      LLM Orchestrator (Ollama)                    |
|   Tools: `get_building_context()`, `set_zone_setpoint()`          |
|   Fallback: Zero-Order Hold (ZOH) on 15s timeout / API error      |
+-------------------------------------------------------------------+
```

---

## Prerequisites

- **Python:** 3.11 or higher
- **Package Manager:** `poetry` (or `uv`)
- **Node.js:** v18 or higher (for React dashboard)
- **Ollama:** Self-hosted or local instance running `qwen2.5:3b-instruct` (or compatible model)

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/tutankhAman/axiom.git
   cd axiom
   ```

2. **Install Python dependencies:**
   ```bash
   poetry install
   ```

3. **Install Dashboard dependencies:**
   ```bash
   cd dashboard
   npm install
   cd ..
   ```

4. **Pull Ollama LLM model:**
   ```bash
   ollama pull qwen2.5:3b-instruct
   ```

---

## Usage Guide

### 1. Run Baseline Simulation (Phase 2)
To run the untouched EnergyPlus baseline simulation and export baseline metrics:
```bash
poetry run python3 main.py --phase 2 --days 4
```

### 2. Run Autonomous Closed-Loop Agent (Phase 5)
To run the AI agent closed-loop optimization with pretty terminal formatting and real-time dashboard streaming:
```bash
# Run 4-day summer peak simulation
poetry run python3 main.py --phase 5 --sync --days 4

# Run 7-day or 14-day simulation
poetry run python3 main.py --phase 5 --sync --days 14
```

### 3. Launch Real-Time Dashboard
In a separate terminal window, start the React dashboard to view live telemetry and metrics:
```bash
cd dashboard
npm run dev
```
Open `http://localhost:5173` in your browser.

### 4. Reset Simulation Outputs & Feeds
To clear previous output CSVs and reset dashboard feeds before running a clean test:
```bash
poetry run python3 scripts/reset_logs.py
```

### 5. Run Unit & Integration Test Suite
```bash
poetry run pytest
```

---

## Project Structure

- `main.py`: Entrypoint for CLI simulation execution (`--phase`, `--sync`, `--days`, `--ablation`).
- `agent/`:
  - `orchestrator.py`: LLM agent tool-calling loop and Zero-Order Hold fallback engine.
  - `mcp_tools.py`: MCP tool definitions (`get_building_context`, `set_zone_setpoint`) and physical safety bounds enforcer.
  - `prefilter.py`: Rule-based trigger engine evaluating PMV thresholds.
  - `pretty_logger.py`: Formatted ANSI console card logging.
  - `live_exporter.py`: Real-time JSON exporter streaming telemetry to the React dashboard.
- `sim/`: PyEnergyPlus runtime API wrappers (`sensors.py`, `actuators.py`, `driver.py`).
- `bridge/`: Thread-safe memory state bridge (`state_bridge.py`).
- `dashboard/`: React + Vite + Tailwind dashboard application.
- `models/`: EnergyPlus building Input Data File (`baseline.idf`) and weather file (`weather.epw`).
- `scripts/`: Data generation and cleanup utilities.
- `.context/`: Technical architecture documents, problem statement, and presentation demo script.
