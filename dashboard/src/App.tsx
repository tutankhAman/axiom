import { useState, useEffect, useRef } from "react"
import SummaryCards from "@/components/SummaryCards"
import PowerChart from "@/components/PowerChart"
import ComfortChart from "@/components/ComfortChart"
import DecisionLog from "@/components/DecisionLog"
import { Badge } from "@/components/ui/badge"
import type { DashboardData } from "@/types"
import initialData from "@/dashboard_data.json"

export default function App() {
  const [data, setData] = useState<DashboardData>(
    initialData as unknown as DashboardData,
  )
  const [isLiveStream, setIsLiveStream] = useState<boolean>(false)
  const [currentStep, setCurrentStep] = useState<number>(0)
  const lastStepRef = useRef<number>(0)

  useEffect(() => {
    let active = true
    let timer: ReturnType<typeof setInterval>

    const fetchLiveData = async () => {
      try {
        const res = await fetch("/live_data.json?t=" + Date.now(), {
          cache: "no-store",
        })
        if (!res.ok || !active) return
        const json = await res.json()
        if (!json?.summary || !json.power_series || !active) return

        const step = json.current_step || 0
        if (step === lastStepRef.current) return
        lastStepRef.current = step

        setData(json as DashboardData)
        setIsLiveStream(Boolean(json.is_live))
        if (step) setCurrentStep(step)

        if (!json.is_live) clearInterval(timer)
      } catch {
        // fallback to static dataset
      }
    }

    fetchLiveData()
    timer = setInterval(fetchLiveData, 2000)

    return () => {
      active = false
      clearInterval(timer)
    }
  }, [])

  const { summary, power_series, pmv_series, decision_log } = data
  const lastHour = power_series[power_series.length - 1]?.hour || 0
  const days = (lastHour / 24).toFixed(1)

  return (
    <div className="min-h-screen bg-background text-foreground antialiased selection:bg-primary/20">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-xl supports-[backdrop-filter]:bg-background/60">
        <div className="max-w-[1440px] mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-baseline gap-4">
            <h1 className="text-sm font-semibold tracking-tight text-foreground">
              Axiom
            </h1>
            <span className="hidden sm:inline-block text-[11px] font-mono text-muted-foreground tracking-wide">
              Closed-Loop HVAC Agent
            </span>
          </div>

          <div className="flex items-center gap-4">
            {isLiveStream ? (
              <Badge variant="success" size="sm" className="gap-1.5 animate-pulse">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
                  <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-success" />
                </span>
                LIVE &middot; Step {currentStep}
              </Badge>
            ) : (
              <Badge variant="secondary" size="sm">
                Simulation Complete
              </Badge>
            )}

            <span className="hidden sm:block text-[10px] font-mono tabular-nums text-muted-foreground">
              {power_series.length.toLocaleString()} t &middot; {days}d
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1440px] mx-auto px-6 py-8 space-y-5">
        {/* Summary KPI cards */}
        <SummaryCards summary={summary} />

        {/* Charts — 2-column grid */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <PowerChart data={power_series} />
          <ComfortChart data={pmv_series} />
        </div>

        {/* Decision Log */}
        <DecisionLog decisions={decision_log} />
      </main>

      {/* Footer */}
      <footer className="border-t border-border/50">
        <div className="max-w-[1440px] mx-auto px-6 py-3 flex items-center justify-between">
          <span className="text-[10px] font-mono text-muted-foreground tracking-wide">
            Axiom &middot; Physical AI BMS
          </span>
          <span className="text-[10px] font-mono text-muted-foreground">
            Honeywell Hackathon
          </span>
        </div>
      </footer>
    </div>
  )
}
