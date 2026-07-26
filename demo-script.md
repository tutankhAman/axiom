# Axiom Eco-Loop Building Agent — PoC Demonstration Script

**Target Duration:** 2 Minutes 15 Seconds (Max 3 Minutes allowed by spec)  
**Format:** Video Screen Recording + Voiceover  
**Objective:** Deliver a 100% score demonstration covering System Integration (30%), Energy Realized (25%), Comfort Bounds (20%), and Agentic Autonomy (15%).

---

## 🎬 Video Production Breakdown

| Timecode | Screen Action (What to Show) | Voiceover Script (What to Say Verbatim) | Key Technical Focus |
| :--- | :--- | :--- | :--- |
| **0:00 – 0:25** *(25s)* | **Screen:** Split screen showing the [architecture diagram](.context/architecture.md) and VS Code with `main.py` and `agent/orchestrator.py`. <br><br>Cursor highlights `PyEnergyPlus` API wrapper and `MCPContext`. | *"Buildings consume forty percent of global energy, mostly because traditional HVAC systems rely on static, rigid schedules. Today we're showing **Axiom**: an autonomous physical AI agent that turns EnergyPlus into a real-time, closed-loop smart building sandbox."* <br><br>*"Instead of giving an open-source LLM unconstrained control, we built a **neuro-symbolic design**. High-level strategic reasoning runs through Ollama tool-calling, while deterministic Python code enforces physical safety bounds."* | Neuro-Symbolic Architecture & MCP Protocol |
| **0:25 – 0:50** *(25s)* | **Screen:** Fullscreen Terminal. <br><br>Type and execute: <br>`poetry run python3 main.py --phase 5 --sync --days 4` <br><br>Show the cyan startup banner printing in terminal. | *"Let's launch the closed-loop controller for a four-day peak summer run. Here in the terminal, PyEnergyPlus streams live zone temperatures, outdoor weather forecasts, and Fanger PMV comfort indices into our StateBridge."* <br><br>*"When a trigger condition occurs, our prefilter invokes Qwen 2.5 via Model Context Protocol tools — specifically `get_building_context` and `set_zone_setpoint`."* | PyEnergyPlus API & Real-Time Tool Calling |
| **0:50 – 1:00** *(10s)* | **Screen:** **FAST-FORWARDED (10x Speed)** clip of the terminal window generating log cards. <br><br>Overlay text on video: `[10x Speed] Simulated 4 Days (384 Timesteps) in Real Time`. | *(Upbeat background track plays quietly. Voiceover speaks over the sped-up clip)* <br><br>*"Over 384 simulation timesteps, the agent continuously monitors zone thermal inertia, automatically floating setpoints during peak pricing windows without human intervention."* | System Integration & Closed-Loop Stability (30% Score) |
| **1:00 – 1:40** *(40s)* | **Screen:** Switch to Browser window running `http://localhost:5173` (React Dashboard). <br><br>1. Hover cursor over the **Summary Cards** (18.1% Savings / 89.6% Comfort). <br>2. Trace cursor along the **HVAC Power Demand Line Chart** comparing Baseline vs Agent. <br>3. Point to the shaded green band in the **PMV Thermal Comfort Chart**. | *"Now let's look at the quantitative results on our live dashboard. Compared to the baseline DOE commercial office, Axiom achieved an **18.1% net reduction in total kWh consumption**."* <br><br>*"Crucially, it didn't save energy by freezing or overheating occupants. In the PMV chart, the green band marks the strict ASHRAE-55 comfort zone between negative point five and positive point five. Axiom held **89.6% comfort compliance**."* <br><br>*"During the two PM to seven PM peak rate window at twenty-five cents per kilowatt-hour, the agent executed a peak-coasting strategy, reducing peak kW demand by over thirty percent."* | Energy Efficiency (25%) & Comfort Compliance (20%) |
| **1:40 – 2:00** *(20s)* | **Screen:** Scroll down on dashboard to the **Decision Log Table**. <br><br>Highlight rows showing `set_zone_setpoint` reasons: *"Peak pricing window ($0.25/kWh): floating cooling setpoint to 27.5°C"*. | *"In the audit log, facility managers can inspect every single decision. If the LLM output ever times out or generates invalid setpoints, our Python safety layer catches it instantly and falls back to a Zero-Order Hold state."* <br><br>*"And at nineteen hundred hours, the prefilter deterministically locks in night setup at twenty-eight point five degrees, eliminating schedule actuator latching bugs."* | Agent Autonomy & Safety Fail-Safes (15%) |
| **2:00 – 2:15** *(15s)* | **Screen:** Return to Dashboard header showing full summary metrics, repository URL text overlay: `github.com/tutankhAman/axiom`. | *"Axiom proves that open-source LLMs paired with standard MCP interfaces and physics-based simulators can deliver immediate, verifiable energy savings in commercial buildings. Thank you."* | Final Wrap-up & Pitch (10%) |

---

## 📽️ Step-by-Step Recording & Prep Guide

### 1. Pre-Recording Setup Checklist
- [ ] **Clean Terminal:** Open terminal window at 1920x1080 resolution, font size 14pt.
- [ ] **Clean Browser:** Open Chrome/Firefox at `http://localhost:5173` in fullscreen or high resolution.
- [ ] **Reset Feeds:** Run `poetry run python3 scripts/reset_logs.py` beforehand so the environment is clean.
- [ ] **Microphone:** Use a clear USB microphone or headset. Record in a quiet room.

### 2. Live Recording Flow
1. **Take 1 (Voiceover & Screen):** Start screen recorder (OBS Studio or Loom).
2. **Action 1 (0:00 - 0:25):** Show VS Code with architecture diagram & code.
3. **Action 2 (0:25 - 0:50):** Switch to terminal and run:
   ```bash
   poetry run python3 main.py --phase 5 --sync --days 4
   ```
4. **Action 3 (0:50 - 1:00):** Let the simulation run for ~10–15 seconds on screen. In your video editor (CapCut, Premiere, or iMovie), speed up this middle portion by **10x** so it takes exactly 10 seconds of screen time.
5. **Action 4 (1:00 - 2:15):** Switch to `http://localhost:5173` and walk through the Summary Cards, Power Chart, Comfort Chart, and Decision Log as scripted above.

---

## 🏆 Rubric Alignment Checklist (How This Script Scores 100%)

- **System Integration (30%):** Highlighted live streaming callbacks between PyEnergyPlus and StateBridge over 384 timesteps.
- **Energy Efficiency Realized (25%):** Explicitly proves **18.1% net kWh reduction** and peak tariff demand reduction on the dashboard chart.
- **Thermal Comfort & Constraints (20%):** Proves **89.6% ASHRAE-55 PMV compliance** inside the shaded `[-0.5, +0.5]` band.
- **Agentic Autonomy & Code Elegance (15%):** Demonstrates MCP tool schemas (`get_building_context`, `set_zone_setpoint`), deterministic prefilter, and ZOH fallback protection.
- **Presentation & Delivery (10%):** Clear, structured narrative under 3 minutes with real-time UI dashboard visualization.
