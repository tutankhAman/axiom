export interface Summary {
  baseline_kwh: number
  closed_loop_kwh: number
  pct_savings: number
  comfort_compliance_pct_baseline: number
  comfort_compliance_pct_closed_loop: number
}

export interface PowerPoint {
  hour: number
  baseline_w: number
  agent_w: number
}

export interface PivotPoint {
  hour: number
  baseline_pmv: number
  agent_pmv: number
}

export interface DecisionEntry {
  hour: number
  day: number
  hour_of_day: number
  zone: string
  heating_c: number
  cooling_c: number
  reason: string
  baseline_pmv: number
  agent_pmv: number
}

export interface DashboardData {
  summary: Summary
  power_series: PowerPoint[]
  pmv_series: PivotPoint[]
  decision_log: DecisionEntry[]
}
