Phase 6 (Revised): Savings Dashboard — No-Fluff Version

Goal: prove the two numbers the rubric actually asks for (% kWh reduction, comfort-boundary compliance), plus the one thing the rubric asks for that the previous spec skipped entirely (visible agent reasoning, for Agentic Autonomy). Nothing else earns its build time today.

Stack
React + Vite (unchanged)
Tailwind + shadcn/ui — use default component styling, don't customize it. Card, Table, Badge, Tabs from shadcn as-is.
Recharts for the two charts
No PapaParse, no client-side CSV parsing, no scroll animations, no texture/glassmorphism, no custom glow effects
Data pipeline

One Python script, run once after Phase 5's two sim runs finish, producing a single dashboard_data.json:

json
{
  "summary": {
    "baseline_kwh": 0,
    "closed_loop_kwh": 0,
    "pct_savings": 0,
    "comfort_compliance_pct_baseline": 0,
    "comfort_compliance_pct_closed_loop": 0
  },
  "power_series": [
    {"hour": 0, "baseline_w": 0, "agent_w": 0}
  ],
  "pmv_series": [
    {"hour": 0, "baseline_pmv": 0, "agent_pmv": 0}
  ],
  "decision_log": [
    {"hour": 0, "zone": "zone1", "heating_c": 0, "cooling_c": 0, "reason": "text from the LLM's tool call"}
  ]
}

Compute pct_savings and comfort compliance % in Python, not in the frontend. The dashboard should do zero math, only render numbers and series it's handed. This also means if your numbers look wrong on demo day, you fix one Python script, not frontend logic.

Components (4 total, no more)

1. Summary row — four shadcn Cards in a row: baseline kWh, closed-loop kWh, % savings (largest text, one accent color, no pulse/glow), comfort compliance %. Static, all visible immediately, nothing animates in.

2. Power comparison chart — Recharts line chart, two lines (baseline vs agent), plain colors (e.g. gray and one accent, not neon-vs-red gradient glow), hover tooltip for exact wattage. X-axis: simulated hours.

3. Comfort band chart — Recharts line/scatter, PMV over time for both runs, with a shaded reference band at [-0.5, 0.5] (ReferenceArea in Recharts, one flat fill color). This is the "we didn't just turn off the HVAC" proof, keep it legible, not busy.

4. Decision log — shadcn Table, columns: hour, zone, setpoint change, reason. This is new versus the original spec and it's the highest-leverage addition: it's the only panel that visibly shows agent reasoning rather than just numbers, and it's the cheapest to build (a table, no custom viz).

Optional 5th panel, only if Phase 6 finishes early: cost/peak-shedding breakdown. Not rubric-scored, don't let it displace panel 4.

Execution steps
npx create-vite@latest dashboard --template react, add Tailwind, add shadcn/ui (npx shadcn@latest init, add card, table, badge components).
Python script: read both result CSVs, compute summary stats + series + decision log, write dashboard_data.json.
Build the 4 components above, static import of the JSON, no loading states needed since it's a static file for a local demo.
Done. Don't add a step 5 for styling polish, the shadcn defaults are the polish.