# Axiom System Architecture

Closed-loop LLM agent for autonomous HVAC control of an EnergyPlus building simulation. The agent monitors thermal comfort (PMV), outdoor conditions, and energy prices, then adjusts zone setpoints via tool calls at 15-minute intervals over multi-day horizons.

## Overview

```
EnergyPlus Engine (pyenergyplus)
    |
    | [timestep callback every 15 min]
    v
SensorManager.fetch_state() -> SimulationState
    |
    v
EnergyPlusDriver.on_timestep
    |
    +-> StateBridge.update_state()
    +-> PreFilter.evaluate()            // deterministic gating
    +-> LLMOrchestrator.evaluate_and_act()  // if triggered
    +-> LiveDashboardExporter.export_snapshot()
    +-> ActuatorManager.set_schedule_value()
```

Two execution modes: **synchronous** (LLM blocks simulation) and **asynchronous** (LLM runs in daemon thread via AgentThread/StateBridge).

---

## Tool Calling Architecture

### Provider and Transport

Ollama (local) accessed through the standard `openai` Python SDK pointed at `http://localhost:11434/v1`. Default model is `qwen2.5:3b-instruct`. The OpenAI SDK is used purely as a transport layer: Ollama exposes an OpenAI-compatible `/v1/chat/completions` endpoint that accepts function-calling payloads.

### Tool Surface

Two tools defined in `agent/mcp_tools.py` using the OpenAI function-calling schema. Registration is a plain Python list (`TOOLS_SCHEMA`) containing two function descriptors:

**`get_building_context`**: Zero parameters. Returns a JSON payload with per-zone temperatures, PMV, PPD, current setpoints, outdoor conditions, 12-hour temperature forecast, energy pricing tier, and HVAC power draw. This is the model's only window into the physical world. No tool call from the LLM actually calls EnergyPlus; the function reads exclusively from the in-memory `StateBridge`.

**`set_zone_setpoint(heating_c, cooling_c, reason)`**: Three required parameters. Applies HVAC setpoints to all zones in the building. The LLM must supply a reason string explaining its decision. This is the only way the agent affects the physical simulation.

### Call Loop

Defined in `agent/orchestrator.py`, method `evaluate_and_act()`:

1. Read latest `SimulationState` from `StateBridge`.
2. Build `get_building_context()` result locally and inject it into the user message as a pre-populated state summary. The LLM does not need to call `get_building_context` as a first turn; it receives the summary inline and can call it again for full details if needed.
3. Construct `messages = [system_prompt, user_content]`.
4. `client.chat.completions.create(messages, tools=TOOLS_SCHEMA, tool_choice="auto", timeout=15.0)`.
5. If the response contains tool calls: execute them locally, append the result as `{"role": "tool", "tool_call_id": id, "content": result}` to the messages list, and loop back to step 4.
6. Loop terminates on one of:
   - `set_zone_setpoint` is executed (success).
   - 3 round-trips completed without a setpoint call (fallback: Zero-Order Hold).
   - Exception or timeout (fallback: Zero-Order Hold).

The LLM typically makes one round-trip: it receives the state snapshot in the user message and calls `set_zone_setpoint` directly. Two-turn patterns occur when it calls `get_building_context` first for deeper zone-by-zone inspection.

### Neuro-Symbolic Safety Layer

The `set_zone_setpoint` function is not a pass-through. Before any LLM-suggested setpoint reaches the building, it is clamped by deterministic rules in `agent/mcp_tools.py` (lines 108-177):

- **Hard bands by time of day**: Occupied morning (25.8-26.5 C), midday (26.5-27.2 C), peak (27.5-28.2 C), unoccupied (fixed 30.0 C). The LLM can suggest any value within these bands; values outside are silently clamped.
- **Minimum deadband**: 2.0 C minimum separation between heating and cooling setpoints. Prevents simultaneous heating and cooling.
- **Dead-band smoothing**: Heating setpoint changes below 0.4 C are suppressed to prevent VAV fan cycling on noise.

This means the LLM operates in a sandbox: it can never command a physically dangerous or energy-wasting setpoint regardless of hallucination quality.

---

## Prompt Engineering Strategy

### System Prompt

There are two system prompts in `agent/orchestrator.py`, selected by CLI flag:

**`COMFORT_SYSTEM_PROMPT`** (default): The agent is told it is an "autonomous BMS agent controlling HVAC setpoints for a commercial office building." The prompt:
- States the objective explicitly: minimize energy while maintaining ASHRAE-55 PMV within [-0.5, +0.5].
- Names the strategy: "PEAK-FLOAT SETPOINT CONTROL." The baseline naturally settles at roughly 25.3 C; floating to 25.8-28.2 C saves energy while staying within comfort bounds.
- Provides a prescriptive three-period decision table with explicit cooling setpoint ranges:
  - Morning (07:00-11:00): 25.8-26.5 C
  - Midday (11:00-14:00): 26.5-27.2 C
  - Peak Coasting (14:00-19:00): 27.5-28.2 C
- Encodes the heating rule: always 15.0 C (summer operation).
- Requires calling `set_zone_setpoint` on every invocation, with a one-sentence reason.

**`ABLATION_SYSTEM_PROMPT`**: Stripped down to the single objective "MINIMIZE HVAC energy, ignore comfort." Used for baseline energy-only experiments.

The decision table in the comfort prompt is the most impactful prompt engineering choice. Rather than expecting the model to discover these bands through exploration, they are given as declarative guardrails. This makes the LLM behave more like a lookup table with natural-language reasoning than a free-form optimizer, which reduces variance across runs.

### User Message

The user message is constructed fresh each timestep. It contains:
- Sim time in hours.
- Comfort status string (compliant / slight drift / violation) with worst-zone PMV.
- Outdoor temperature and 12-hour forecast trend.
- Time-of-day pricing tier (on-peak / off-peak).
- Current HVAC power demand in watts.
- An instruction to optionally call `get_building_context` for full details, then call `set_zone_setpoint`.

The message is always one short paragraph. No conversation history is accumulated across timesteps. Each LLM invocation is stateless: it sees only the current snapshot. Prior decisions persist indirectly through the `StateBridge` actuator state, which uses Zero-Order Hold between LLM invocations.

### Tool Descriptions as Prompt Material

The `set_zone_setpoint` tool description in `TOOLS_SCHEMA` repeats the time-of-day bands and the heating fixed-at-15 rule. This acts as a secondary prompt: even if the model ignores the system prompt, it sees the constraints again in the tool parameter descriptions.

---

## Latency Management

### Primary Strategy: Deterministic Gating (PreFilter)

The LLM does not run on every 15-minute timestep. A PreFilter (`agent/prefilter.py`) gates LLM invocation:

- **Unoccupied hours**: LLM never fires. A deterministic rule sets cooling to 30.0 C and heating to 15.0 C. The simulation can run through nights and weekends with zero API calls.
- **Optimum start** (05:00-07:00 on workdays): Building is pre-conditioned to 25.8 C without LLM involvement.
- **Trigger conditions**: LLM fires only when any zone exceeds PMV +-0.5, or on a periodic interval (default 1 hour).
- **Minimum cooldown**: 0.5 hours between consecutive triggers. Prevents rapid re-triggering during transient states.

Net effect: roughly 24 LLM calls over a 96-hour simulation (384 possible timesteps). That is a 94% reduction in invocation rate.

### API Timeout

Every LLM call has a 15-second hard timeout via the OpenAI SDK `timeout` parameter. If the timeout fires, the exception is caught and the last valid setpoint is maintained (Zero-Order Hold).

### Turn Limit

The tool-calling loop caps at 3 round-trips. After 3 turns without a `set_zone_setpoint` call, the loop exits and holds the last setpoint. This prevents runaway tool-calling when the model is indecisive or hallucinates non-existent tools.

### Async Execution

When running in `--exec async` mode, the LLM runs in a daemon thread (`agent/thread.py`). The main simulation thread does not block. The `StateBridge` uses `threading.Lock` for state access and `threading.Event` for signaling. If the LLM is still running when the next timestep fires, the simulation proceeds with the current setpoint and the agent thread publishes its result when ready. Agent thread shutdown uses a 20-second timeout (covering the 15-second API timeout plus processing overhead).

### ZOH Fallback

Any failure path (timeout, exception, no setpoint in 3 turns, PreFilter suppression) results in Zero-Order Hold: the last actuation command remains in effect. The simulation never crashes due to LLM unavailability.

---

## Handling Long Simulation Logs

### Terminal Output

`agent/pretty_logger.py` implements a sampling approach rather than full verbosity. A full timestep card is printed only:
- Every 8th tick (every 2 hours) for periodic status.
- On every LLM trigger event (PMV violation or interval).

This means during long unoccupied stretches, the terminal is silent. During active periods with frequent triggers, the output remains readable because cards are printed at the trigger rate (at most once per 0.5 hours due to cooldown).

Each timestep card is a single block of ANSI-colored text showing the critical snapshot: sim time, outdoor temp, zone temps, PMV with color coding (green/amber/red), HVAC power, active setpoints, and the raw LLM reason text. Cards are separated by empty lines for visual scanning.

### CSV History

`main.py` exports full simulation history to CSV at the end of the run. Every timestep is recorded: sim time, outdoor temp, HVAC power, per-zone temperatures, PMV, and PPD. No truncation. This is the ground truth for analysis scripts.

### Dashboard Export

`agent/live_exporter.py` writes JSON to `dashboard/public/live_data.json` using atomic replacement (write to `.tmp` then `os.replace`). The dashboard polls this file every 2 seconds. The exporter:

- Deduplicates consecutive identical entries in the decision log to avoid flooding the UI with repeated setback entries.
- Sends all historical data (no truncation). For a 96-hour simulation this is roughly 384 power/PMV data points and up to 100 decision log entries. These numbers are well within the React dashboard's rendering budget.
- Computes cumulative energy (kWh) and comfort compliance percentages incrementally for the summary cards.

### LLM Context

The LLM does not see logs. Each `evaluate_and_act()` call builds a fresh `messages` list with only the system prompt and a short current-state summary. There is no conversation history, no accumulated context, and no truncation strategy needed. The model's context window is consumed only by the system prompt plus roughly 500 tokens of current state data. For a 3B parameter model, this leaves substantial headroom.

---

## Thread Safety Model

`bridge/state_bridge.py` implements a single-lock, single-event pattern:

- `threading.Lock` guards all reads and writes to the shared state (`SimulationState`, actuation commands, trigger flag).
- All getter methods return copies (shallow dict copies via `.copy()`) to prevent mutation races between the simulation thread and the agent thread.
- `threading.Event` signals the agent thread when a new trigger condition is set. The agent thread polls `trigger_event.wait(timeout=0.1)` in a loop for graceful shutdown detection.
- The simulation thread writes first, then signals. The agent thread reads after the signal. This ordering plus the lock ensures the agent always sees the state that triggered it.

---

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point, simulation lifecycle, CSV export |
| `agent/orchestrator.py` | System prompts, LLM tool-calling loop, timeout handling |
| `agent/mcp_tools.py` | Tool definitions (schema + implementations), safety clamping |
| `agent/prefilter.py` | Deterministic trigger gating, night setback, optimum start |
| `agent/thread.py` | Async agent worker thread |
| `agent/pretty_logger.py` | Terminal output with ANSI coloring and sampling |
| `agent/live_exporter.py` | Dashboard JSON export with atomic writes |
| `agent/epw_reader.py` | EPW weather file parser for 12-hour forecast |
| `bridge/state_bridge.py` | Thread-safe shared state with lock and event |
| `sim/sensors.py` | EnergyPlus variable handle management, SimulationState dataclass |
| `sim/driver.py` | EnergyPlus runtime wrapper, callback registration |
| `sim/actuators.py` | Schedule actuator handle resolution and writing |
