# Eco-Loop — Solo 24hr Implementation Plan

Budget: ~22 working hours out of the 24 available, 2hr held back as a real buffer (see Phase 8). Every phase has an exit criterion. If you miss one, cut scope inside that phase before you let it eat time from the next one.

Two scope cuts from the architecture doc, made specifically because this is solo/clean-slate/24hr, not because they're wrong in general:

- **Redis is out.** Use an in-process shared dict + `threading.Lock` for the state bridge instead. Same decoupling property (agent thread failing doesn't kill the sim thread), zero extra infra to install, configure, or keep alive during recording. Mention this substitution explicitly in your architecture doc, don't just silently deviate.
- **Simulated horizon is short.** Run 1-2 simulated weeks, not a year. Long enough to show a believable % savings number, short enough that a full test cycle takes minutes instead of hours. You will run this loop dozens of times while debugging; a year-long run turns every bug into a 40-minute wait.

## Phase 0 — Environment, 0:00–1:30

Your top technical risk today isn't the agent logic, it's getting `pyenergyplus` importable on CachyOS. Prebuilt EnergyPlus installers are usually linked against an Ubuntu LTS glibc; Arch/CachyOS ships newer glibc and this occasionally breaks the bundled Python extension.

- Try the native Linux `.run` installer first (from the EnergyPlus GitHub releases). Set `PYTHONPATH` to the install directory so `import pyenergyplus` resolves.
- Hard timebox: 30 minutes. If you're fighting linker errors past that, stop and pull the official `nrel/energyplus` Docker image instead, mount your working directory as a volume, and run your driver script inside the container. Don't debug glibc compatibility on hackathon day.
- Switch your GPU mode via `envycontrol` to hybrid/nvidia now, not integrated. Confirm with `nvidia-smi`. Ollama on CPU-only will blow your latency budget for the whole day.
- Check actual free VRAM before picking a model. Under ~10GB, pull Qwen2.5 7B-instruct or Qwen3 8B, not the 27B/35B-class models — those need 18-24GB and won't fit a laptop GPU. Pull it now, test one tool-call round trip with `curl` against Ollama's OpenAI-compatible endpoint before you build anything on top of it.
- Exit criteria: `pyenergyplus` imports and prints an API version; `nvidia-smi` shows the model loaded on GPU; one manual tool-call test against Ollama returns a valid structured response.

## Phase 1 — Building model + read-only loop, 1:30–4:00

- Pull a ready-made small office IDF + matching EPW (Sinergym's bundled 5-zone model, or a DOE ASHRAE 90.1 prototype office). Do not model a building from scratch today.
- Write the driver script. Register sensor handles: zone mean air temp, `Zone Thermal Comfort Fanger Model PMV`/`PPD`, facility HVAC electricity demand rate, outdoor drybulb temp.
- Check the People object in your IDF has a Fanger thermal comfort model selected before you assume PMV/PPD will show up in the output — this is the single most common miss and it's invisible until you go looking for a variable that was never generated.
- A callback on `callback_end_zone_timestep_after_zone_reporting` that just prints state to console.
- Exit criteria: a short test run (a day or two of simulated time) prints live sensor values, no crash.

## Phase 2 — Actuator writes + baseline run, 4:00–7:00

- Find the `Schedule:Constant`/`Schedule:Compact` objects driving your heating/cooling setpoints. Get actuator handles via the `Schedule Value` actuator type.
- Write a callback that overrides them with a hardcoded test value, confirm the override actually changes zone behavior versus an un-actuated run (don't just trust that the write succeeded, check the sim's response).
- Run your untouched baseline (fixed schedule, no actuation) over your chosen short horizon. Save results to CSV.
- Exit criteria: `baseline.idf` runs clean end to end, actuator override is proven to affect the sim, baseline results saved.

## Phase 3 — In-memory state bridge + pre-filter, 7:00–9:00

- Shared dict + lock between the sim thread and a second "agent" thread. This is your state bridge.
- Deterministic pre-filter, no model call yet: PMV outside [-0.5, 0.5], or a fixed control interval elapsed (every simulated hour, say). Sets a flag for the agent thread to act.
- Exit criteria: sim runs continuously, agent thread wakes on trigger and just logs "would call LLM now."

## Phase 4 — MCP tools + LLM decision loop, 9:00–13:00

This is the longest phase and the one most likely to run over. Protect it.

- Tools: `list_zones`, `get_zone_state`, `get_facility_meters`, `get_grid_context` (static CSV aligned to your EPW timestamps, not a live API call, don't add a network dependency to your control loop on demo day), `set_zone_setpoint(zone_id, heating_c, cooling_c, reason)` with `reason` mandatory.
- Wire Ollama's tools API. One batched prompt covering all zones per invocation, not one call per zone.
- Actuator callback always writes the last known decision (zero-order hold), independent of whether a new one has arrived.
- Fallback path: LLM timeout or malformed tool call → keep the last good setpoint, log the fallback, never let an agent-side exception propagate into the sim thread.
- Clamp every setpoint server-side in the tool handler before it reaches EnergyPlus, regardless of what the schema says the model should return.
- Exit criteria: full closed loop runs top to bottom on a short test horizon without crashing, and you can see setpoints changing in the log with a reason attached to each one.

## Phase 5 — Full comparison run, 13:00–16:00

- Run `closed_loop.idf` over the same horizon and EPW as your baseline.
- Compute % kWh reduction, plot PMV distribution for both runs.
- Only if you're ahead of schedule: run the energy-only ablation (strip the comfort constraint from the prompt) as a bonus differentiator for the write-up. Skip without guilt if you're not.
- Exit criteria: two result CSVs with real numbers, neither run crashed.

## Phase 6 — Dashboard, 16:00–18:00

- Single HTML/React artifact reading your two static result CSVs. No live Redis/socket reads needed here, a static comparison built after your runs finish is far less fragile to record than something live.
- Three panels minimum: cumulative kWh baseline vs closed-loop, PMV histogram both runs, timeline of setpoint changes with their logged reasons.
- Exit criteria: dashboard shows your actual numbers, not placeholders.

## Phase 7 — Docs, slides, video, 18:00–21:00

- Update `architecture.md` to describe what you actually built, including the Redis→in-memory substitution and why. Judges read an honest documented tradeoff as more credible than a doc that pretends everything went exactly to the original plan.
- Fill the provided presentation template with your real numbers and a screenshot of the reason-timeline panel.
- Script the video narration before you hit record. Show: EnergyPlus stepping through simulated time, the agent logging a tool call and its reason, the actuator write landing, the dashboard number updating. Under 3 minutes, one take if the script is tight.

## Phase 8 — Buffer, 21:00–24:00

If you're done by hour ~18-19, stop and take a real 2-3hr break before video/slides. A tired script is a worse script and you'll end up re-recording anyway, that costs more time than the break does.

If you're behind: this is your only remaining slack. Spend it making the existing loop not crash, not adding features. A working baseline-vs-closed-loop comparison with a rough dashboard beats a broken pipeline with a polished one, given System Integration is 30% of the score and Presentation is 10%.
