# Eco-Loop Building Agents — System Architecture

## 0. Design priorities, mapped to the rubric

Weights: System Integration 30%, Energy Efficiency 25%, Comfort 20%, Agentic Autonomy 15%, Presentation 10%.

System Integration is the single biggest line item and it is entirely about one thing: the loop must run for an extended horizon without EnergyPlus crashing or the agent stalling it. Every design decision below is made in that order: don't crash, then save energy, then don't sacrifice comfort to do it, then make the agent story compelling, then make it look good. A team that ships a fragile but clever agent loses more points than a team that ships a boring but bulletproof one.

## 1. Component overview

```
EnergyPlus (Python API, in-process)
   |  reads: zone temp, PMV/PPD, HVAC electricity demand, outdoor temp
   |  writes: heating/cooling setpoint schedules (actuator overrides)
   v
State Bridge (Redis)  <-- decouples sim thread from agent thread
   |
   v
Pre-filter (deterministic Python, no LLM call)
   |  only escalates when a rule threshold is crossed
   v
MCP Server (custom tools: get_zone_state, get_facility_meters,
            get_grid_context, set_zone_setpoint, list_actuators)
   |
   v
LLM Agent (Qwen3.6 or Llama 3.3, served via Ollama, tool-calling loop)
   |  writes decision + justification back to Redis
   v
State Bridge --> EnergyPlus actuator write (zero-order hold until next decision)
   |
   v
Dashboard (reads Redis / a results DB, live during demo)
```

Everything downstream of EnergyPlus is decoupled through Redis so a slow or crashed LLM call never blocks or kills the simulation thread. This single decision is what protects your 30%.

## 2. Simulation layer

Use `pyenergyplus.api.EnergyPlusAPI`, calling EnergyPlus as a library from a Python driver script (not the Python Plugin mode — library mode gives you a single external controller process, which is what you want for an agent loop and what the deliverable "unified codebase" implies). EnergyPlus's own EMS API is what you're wrapping either way; the difference is just who owns the process.

**Base building model.** Don't model a building from scratch under hackathon time pressure. Two credible fast paths:

- Pull a prototype IDF from Sinergym's bundled models (e.g. the 5-zone office) or a DOE prototype building (ASHRAE 90.1 Medium Office). These already have working HVAC objects, occupancy schedules, and thermostats, so you spend your time on the agent, not on building physics debugging.
- Don't import Sinergym as a dependency for your control loop, though — it's a Gymnasium/RL wrapper, and the hackathon wants to see your own EnergyPlus API wrapper and MCP tool layer, not someone else's RL abstraction sitting between you and the sim. Use its IDF/EPW as your starting building, write your own thin wrapper directly against `pyenergyplus`.

**Sensors** (via `api.exchange.get_variable_handle`, registered after warm-up):
- `Zone Mean Air Temperature`
- `Zone Thermal Comfort Fanger Model PMV` / `...PPD` (per zone, requires a `People` object with a Fanger thermal comfort model selected — check this is enabled in your IDF or these variables won't show up in the RDD)
- `Facility Total HVAC Electricity Demand Rate`
- `Site Outdoor Air Drybulb Temperature`

**Actuators** (via `api.exchange.get_actuator_handle`): don't rewrite `ZoneControl:Thermostat` objects directly. Cleanest path is to actuate the `Schedule:Constant` or `Schedule:Compact` objects that drive your heating/cooling setpoint schedules using the `Schedule Value` actuator type. The LLM sets an arbitrary numeric setpoint, you write it to the schedule actuator, EnergyPlus's own HVAC managers do the rest. This avoids fighting EnergyPlus's built-in thermostat control logic.

**Calling points.** Read state after the zone timestep is finalized (`callback_end_zone_timestep_after_zone_reporting`). Write actuator overrides before the predictor/HVAC managers run for that step so the new setpoint is respected in that step's HVAC solve — this is typically a calling point named around `callback_after_predictor_before_hvac_managers` or `callback_begin_system_timestep_before_predictor`, but verify the exact name against your installed EnergyPlus version's `pyenergyplus/api.py`; calling point names have shifted slightly across versions and getting this wrong silently gives you a one-step-stale control loop, which is the kind of bug that's invisible until someone asks why your savings curve looks off by one step.

**Clamp actuator writes server-side** (in the MCP tool, before the value ever reaches EnergyPlus) to a physically valid range for the zone. An out-of-range actuator write is one of the more common ways to crash or corrupt a long EnergyPlus run, and it's entirely preventable input validation. This is a System Integration point, treat it as non-optional.

## 3. State bridge: why decoupling matters here

EnergyPlus's calling points run synchronously in the same thread as `run_energyplus()`. If you call your LLM directly inside a callback, the simulation blocks on network I/O to Ollama for every decision. For a hackathon demo this isn't fatal (simulated time isn't real-world time, EnergyPlus just runs slower wall-clock), but it does three things you don't want: it makes a single hung LLM call kill your entire run, it makes it hard to show a live-updating dashboard concurrently, and it couples your control cadence to your callback frequency by accident.

Given you already know RabbitMQ/Redis from Larity, use the same pattern here:

- EnergyPlus's reporting callback pushes a state snapshot to a Redis key every zone timestep.
- A separate async agent process consumes state, runs the pre-filter, and (when triggered) calls the LLM/MCP tool chain, then writes the resulting setpoint to a Redis key.
- EnergyPlus's actuator-write callback reads the latest value from that key every timestep (zero-order hold — if no new decision has arrived, keep the last one). Non-blocking, EnergyPlus never waits on the agent.

This buys you three separate, independently-crash-safe processes for the demo video: sim, agent, dashboard, all watchable live and all recoverable if one hiccups.

## 4. Decision cadence: don't call the LLM every timestep

A year-long run at 10-minute zone timesteps is ~52,000 steps. Calling an LLM at every one of those is both slow and pointless (nothing meaningfully changes zone-to-zone in 10 minutes). This is the same tiered-cost problem Larity's pipeline already solves with its pre-filter/classification stages before the expensive reasoning call, apply the same idea here:

1. **Deterministic pre-filter** (plain Python, no model call): is PMV outside [-0.5, 0.5] (ASHRAE 55 comfort band)? Is HVAC demand within some delta of a peak threshold? Has time-of-use pricing or a fixed carbon-intensity schedule crossed a boundary? If none of these fire and the fixed control interval hasn't elapsed, skip the LLM call entirely and hold the last setpoint.
2. **Fixed control interval** as a floor even when nothing's flagged, e.g. re-evaluate every simulated hour, so the agent still adapts to slow drift (outdoor temp ramping through the day) even without a discrete trigger.
3. **Batch zones into one prompt.** If the building has 5 zones, send one call with all 5 zone states and let the model reason across them and return 5 setpoints, instead of 5 separate calls. Cuts call count by the zone count for free.

Expect this to cut LLM call volume by roughly an order of magnitude versus naive per-timestep invocation, which is also your answer for the "latency management" section of the required architecture write-up.

## 5. Cognitive engine

Serve locally via Ollama for setup reliability during the demo (no external API dependency to fail on stage). Model choice as of mid-2026: Qwen3.6 (27B dense or the 35B-A3B MoE variant) has closed most of the tool-calling reliability gap to frontier cloud models and runs on consumer VRAM tiers (18-24GB); Llama 3.3 70B is a solid dense fallback if you have 48GB+. Use Ollama's OpenAI-compatible tools API rather than parsing free-text output, structured tool calls are far more robust for a control loop than regex-scraping a setpoint out of prose.

**MCP tool surface** (your own server, not a reuse of the existing EnergyPlus-MCP project — that project's 35 tools are built for offline model editing, validation, and batch simulation runs, a different job from a live sub-hourly control loop. Worth citing as prior art for the "MCP + EnergyPlus" pairing and worth borrowing its layered protocol/tools/orchestration/integration split for your own code organization, but not worth adopting wholesale):

- `list_actuators()` / `list_zones()` — discovery, so the model never has to guess or hallucinate a zone name
- `get_zone_state(zone_id)` — temp, PMV, PPD, humidity
- `get_facility_meters()` — current HVAC electricity demand, cumulative kWh so far this run
- `get_grid_context()` — outdoor temp plus a static time-of-use price / carbon-intensity schedule (see note below on why static, not live)
- `set_zone_setpoint(zone_id, heating_c, cooling_c, reason)` — the `reason` field is mandatory in your schema; it's your audit trail and it's what makes "Agentic Autonomy" visible to judges instead of a black box
- `get_recent_errors(n)` — tails only severe/fatal lines from the current run's err stream, see §6

**On grid carbon intensity:** don't call a live external API (WattTime, ElectricityMaps) during the actual demo run. A network call from inside your control loop during a live recording is an unforced reliability risk for zero score benefit, since the hackathon doesn't require real grid data. Bake a synthetic time-of-day carbon-intensity or price curve into a CSV aligned with your EPW timestamps instead, and just cite that it's a stand-in for a live feed in your architecture doc.

## 6. Handling lengthy simulation logs

EnergyPlus `.err` files on a long run can run thousands of lines. Never feed the full log to the LLM. A sidecar tails the file, filters for lines starting `** Severe **` or `** Fatal **` plus a couple lines of surrounding context, and that's the only log content that ever enters a prompt (via `get_recent_errors`). This keeps context small and cheap, and it's a real answer to the "handling lengthy simulation logs" deliverable requirement rather than a hand-wave.

## 7. Experiment design (this is where you win Energy Efficiency + Comfort points)

Run three variants over the same building, same EPW, same horizon, so the comparison is fair:

1. **Baseline**: fixed rule-based setpoint schedule (whatever a conventional BMS would run).
2. **Closed-loop, comfort-constrained**: your LLM agent with the ASHRAE 55 comfort band enforced in the system prompt and pre-filter.
3. **Closed-loop, energy-only ablation** (optional but a strong differentiator): same agent with comfort constraints removed, to explicitly demonstrate the tradeoff and prove variant 2's comfort awareness is doing real work, not free.

Most teams will only submit variant 1 vs 2. Variant 3 turns your submission into an actual experiment instead of a demo, and it directly targets both the 25% and 20% criteria at once by making the tradeoff visible instead of asserted.

## 8. Dashboard

Build this as a single HTML/React artifact (or a lightweight local web app) reading from Redis or a results SQLite/CSV export. Show, minimum:
- Baseline vs closed-loop kWh over the run, cumulative
- PMV distribution (histogram) for baseline vs closed-loop, to visually prove comfort wasn't sacrificed
- A timeline of every `set_zone_setpoint` call with its `reason` string, this is the single highest-leverage visual for the Agentic Autonomy criterion because it's the only place judges see the model actually reasoning rather than just producing a number

## 9. Repo structure

```
eco-loop/
  sim/                  # EnergyPlus driver, callbacks, actuator/sensor handles
  bridge/                # Redis state bridge, zero-order hold logic
  agent/
    prefilter.py         # deterministic trigger logic
    mcp_server.py         # tool definitions
    orchestrator.py       # Ollama tool-calling loop, prompt templates
  models/
    baseline.idf
    closed_loop.idf       # same building, actuator-ready
    weather.epw
  dashboard/              # HTML/React visualization
  docs/
    architecture.md        # this document, expanded with your actual numbers
  results/
    baseline_run.csv
    closed_loop_run.csv
    ablation_run.csv        # if you do variant 3
```

## 10. Demo video plan (maps directly to what the rubric asks the video to show)

Split-screen or sequential cuts of: (1) terminal showing EnergyPlus stepping through simulated time, (2) the agent process logging a pre-filter trigger firing, an MCP tool call, and the model's returned setpoint + reason, (3) the actuator write landing back in EnergyPlus's next timestep, (4) the dashboard's cumulative savings number ticking. That sequence is a literal checklist match against "data transferring live from EnergyPlus to the LLM and the subsequent control actions updating the model parameters automatically."

## 11. Failure handling checklist (System Integration, 30%, don't skip this)

- Actuator writes clamped server-side before touching EnergyPlus.
- LLM call timeout or error: fall back to last known-good setpoint, log the fallback, never crash the sim thread on an agent failure.
- Redis unavailable: agent halts gracefully, EnergyPlus keeps running on zero-order hold indefinitely (it should never depend on Redis being up to keep simulating).
- Sanity-check the model's returned setpoints server-side against the zone's physical bounds before writing, even though the MCP tool schema should already constrain it, defense in depth for a live demo.

## References / prior art worth citing in your write-up

- Li, Xu, Hong, "EnergyPlus-MCP: A model-context-protocol server for AI-driven building energy modeling," SoftwareX, 2025, first open-source MCP server for EnergyPlus, 35 tools across model management/editing/HVAC inspection/simulation execution. Different job (offline model editing) from your real-time control loop, cite as the concept's origin.
- Sinergym (Jiménez-Raboso et al., BuildSys 2021, arXiv:2412.08293) — Gymnasium interface over the EnergyPlus Python API, useful as a source of pre-built building models and as a reference for clean actuator/sensor wrapper design, not as a dependency for your control loop.
- EnergyPlus Python API / EMS documentation (`pyenergyplus`), Department of Energy, for calling point and actuator/sensor handle semantics.
