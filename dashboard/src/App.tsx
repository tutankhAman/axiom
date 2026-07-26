import SummaryCards from "@/components/SummaryCards"
import PowerChart from "@/components/PowerChart"
import ComfortChart from "@/components/ComfortChart"
import DecisionLog from "@/components/DecisionLog"
import { Separator } from "@/components/ui/separator"
import type { DashboardData } from "@/types"
import data from "@/dashboard_data.json"

const typedData = data as unknown as DashboardData

export default function App() {
  const { summary, power_series, pmv_series, decision_log } = typedData
  const lastHour = power_series[power_series.length - 1]?.hour || 0
  const days = Math.round(lastHour / 24)

  return (
    <div className="min-h-screen bg-background antialiased">
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="max-w-7xl mx-auto px-5 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-base font-semibold tracking-tight">Axiom</h1>
            <p className="text-xs text-muted-foreground">
              Closed-Loop HVAC Agent &mdash; Simulation Results
            </p>
          </div>
          <span className="text-[11px] text-muted-foreground font-mono tabular-nums">
            {power_series.length} timesteps &middot; {days} days
          </span>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-5 py-6 space-y-6">
        <SummaryCards summary={summary} />

        <Separator />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <PowerChart data={power_series} />
          <ComfortChart data={pmv_series} />
        </div>

        <Separator />

        <DecisionLog decisions={decision_log} />
      </main>

      <footer className="border-t mt-8">
        <div className="max-w-7xl mx-auto px-5 py-3 text-[11px] text-muted-foreground">
          Axiom &middot; Phase 6 Dashboard
        </div>
      </footer>
    </div>
  )
}