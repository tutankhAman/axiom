import { useState, useEffect } from "react"
import SummaryCards from "@/components/SummaryCards"
import PowerChart from "@/components/PowerChart"
import ComfortChart from "@/components/ComfortChart"
import DecisionLog from "@/components/DecisionLog"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import type { DashboardData } from "@/types"
import initialData from "@/dashboard_data.json"

export default function App() {
  const [data, setData] = useState<DashboardData>(initialData as unknown as DashboardData)
  const [isLiveStream, setIsLiveStream] = useState<boolean>(false)
  const [currentStep, setCurrentStep] = useState<number>(0)

  // Real-time polling hook for live simulation feed
  useEffect(() => {
    const fetchLiveData = async () => {
      try {
        const res = await fetch("/live_data.json?t=" + Date.now(), { cache: "no-store" })
        if (res.ok) {
          const json = await res.json()
          if (json && json.summary && json.power_series) {
            setData(json as DashboardData)
            setIsLiveStream(Boolean(json.is_live))
            if (json.current_step) setCurrentStep(json.current_step)
          }
        }
      } catch (err) {
        // Fallback silently to initial static dataset if live feed not present
      }
    }

    // Poll every 1000ms
    const interval = setInterval(fetchLiveData, 1000)
    fetchLiveData() // Immediate check

    return () => clearInterval(interval)
  }, [])

  const { summary, power_series, pmv_series, decision_log } = data
  const lastHour = power_series[power_series.length - 1]?.hour || 0
  const days = (lastHour / 24).toFixed(1)

  return (
    <div className="min-h-screen bg-background antialiased text-foreground">
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="max-w-7xl mx-auto px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div>
              <h1 className="text-base font-semibold tracking-tight flex items-center gap-2">
                Axiom
                <span className="text-xs font-normal text-muted-foreground">
                  (Closed-Loop HVAC Agent)
                </span>
              </h1>
              <p className="text-xs text-muted-foreground">
                Physical AI Proof-of-Concept &mdash; Real-Time Performance Monitor
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {isLiveStream ? (
              <Badge variant="outline" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 px-3 py-1 text-xs gap-2 animate-pulse">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                LIVE STREAMING (Step #{currentStep})
              </Badge>
            ) : (
              <Badge variant="secondary" className="px-3 py-1 text-xs text-muted-foreground">
                ✓ SIMULATION COMPLETE
              </Badge>
            )}

            <span className="text-[11px] text-muted-foreground font-mono tabular-nums">
              {power_series.length} timesteps &middot; {days} days
            </span>
          </div>
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
        <div className="max-w-7xl mx-auto px-5 py-3 text-[11px] text-muted-foreground flex justify-between">
          <span>Axiom &middot; Physical AI Building Management System</span>
          <span>Honeywell Hackathon Submission</span>
        </div>
      </footer>
    </div>
  )
}