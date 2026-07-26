# Axiom — Demo Script (Solo, ~2:30)

**Format:** Screen recording with live voiceover. One take, no cuts mid-sentence.
Record in this order, speaking naturally as you go. Don't read verbatim — these are your talking points. If you stumble, keep going; the point is to sound like you know the code, not like you memorized a script.

---

## Setup before recording

- **Terminal:** 1920x1080, font size 14, dark theme, already in the `axiom/` directory
- **Browser:** `http://localhost:5173` loaded and showing the dashboard (pre-run data, or static fallback)
- **Dashboard** should already be running (`npm run dev` in `dashboard/`)
- **Ollama** should be running with Qwen2.5 loaded
- Run `uv run python scripts/reset_logs.py` first if you want clean logs

---

## 0:00–0:25 — The problem and how I approached it

**Show:** VS Code with `agent/mcp_tools.py` open on one side, the architecture diagram on the other.

**Say (in your own words):**

*Buildings eat about 40% of global energy. Most of them run their HVAC on a dumb schedule — 24 degrees from 7 AM to 7 PM, no matter what's happening outside or how much power costs.*

*I wanted to see if a local open-source LLM could do better. So I built Axiom. It's a closed loop: EnergyPlus simulates a commercial building, an LLM reads live sensor data from it, makes control decisions, and those decisions go right back into the simulation. All in real time, no human in the loop.*

*The thing I spent the most time on wasn't the LLM — it was the safety layer around it. The LLM suggests setpoints, but Python enforces physical bounds, handles night setbacks deterministically, and falls back to the last good setpoint if the model times out or returns garbage.*

---

## 0:25–0:55 — Launching the closed loop

**Show:** Switch to terminal. Run the command, let the banner print.

```bash
uv run python main.py --phase 5 --sync --days 4
```

**Say:**

*Let me kick off a 4-day summer run. The building model is a DOE medium office — five thermal zones, July in Denver, outdoor temps hitting the mid-30s. The baseline just holds 24 degrees all day. My agent is allowed to float the cooling setpoint between about 25 and a half and 26 and a half during occupied hours, and it backs off to 30 at night.*

*You can see the terminal printing live state cards as EnergyPlus steps through. Each one shows outdoor temp, zone temp, PMV comfort index, and the current setpoint. When you see "LLM DECISION" on a card, that means the prefilter decided conditions warranted a model call.*

*Let me fast-forward through the bulk of the run.*

---

## 0:55–1:05 — Speed-through

**Show:** Pre-recorded 10x speed clip of the terminal scrolling through timestep cards, with overlay text `[10x speed — 96 simulated hours, ~24 LLM decisions]`.

**Say (voiceover over the sped-up clip):**

*Over 96 simulated hours, the prefilter invokes the LLM about two dozen times. The rest of the time, it holds the last setpoint or runs a deterministic rule — night setback at 7 PM, optimum start at 5 AM. The simulation stays stable the whole time; if EnergyPlus crashes or the model hangs, the loop keeps running on the last known good state.*

---

## 1:05–1:45 — Dashboard results

**Show:** Switch to browser at `localhost:5173`. Point with cursor as you talk.

**Say:**

*Here's the dashboard. Let me walk through what happened.*

*Top row — summary cards. Baseline pulled about 118 kilowatt-hours over four days. My agent pulled around 89. That's about 25% less. And comfort compliance — this is percentage of occupied hours where PMV stayed inside ASHRAE-55, which is plus or minus 0.5. Agent held 100%.*

*The power chart — gray line is baseline, blue line is the agent. You can see the baseline chiller kicking on hard during the day, pulling 5, 6 kilowatts. The agent runs the chiller less aggressively during peak hours — it's letting the building coast a bit, floating the temperature up during the afternoon when electricity is most expensive.*

*The comfort chart — same idea, but showing PMV over time. Green band in the middle is the ASHRAE comfort zone. The agent line stays inside it the whole time. The baseline line drifts above it during the afternoon because the baseline doesn't adapt — it just runs a fixed schedule.*

---

## 1:45–2:15 — Audit trail and why it matters

**Show:** Scroll down to the Decision Log table. Hover over a couple of rows.

**Say:**

*Scroll down to the decision log. Every time the LLM or the prefilter changed a setpoint, it gets logged here — what hour, what setpoint, and the reason string the model provided.*

*This is actually the thing I'm most proud of. Building operators don't trust black boxes, and they shouldn't. Every decision is traceable. You can see exactly when the model chose to float the temperature and why.*

*A few things to call out. One, the heating setpoint is always 15 degrees — it's summer, heating is dead. The system doesn't pretend to make heating decisions when there's nothing to decide. Two, at 7 PM every day the prefilter forces a 30-degree setback — that's deterministic, the LLM never touches it, and it eliminates a whole class of bugs where the model forgets to unwind the daytime setpoint and the chiller runs all night.*

*And three, if the LLM times out or returns something invalid — which can happen with local models — there's a zero-order hold fallback. The loop doesn't crash, it just keeps the last good setpoint and logs the failure.*

---

## 2:15–2:30 — Closing

**Show:** Scroll back up to the dashboard header. Repository URL overlay: `github.com/tutankhAman/axiom`

**Say:**

*So to wrap up — Axiom is a proof of concept that an open-source LLM running locally, paired with a physics simulation and a safety-first Python layer, can autonomously run a building. 25% energy savings, 100% comfort compliance, and a fully auditable decision trail. All of it runs on a single machine — the simulation, the model, and the dashboard.*

*The code is at the link on screen. Thanks for watching.*

---

## Post-recording notes

- If the dashboard numbers differ from the script (e.g., you ran a different config), just say whatever the actual numbers are. The script is a guide, not a teleprompter.
- If you trip over a word, pause, take a breath, restart the sentence. Natural pauses make you sound like a person, not a robot.
- The absolute worst thing you can do is sound like you're reading. Talk like you're explaining your project to a colleague over coffee.
