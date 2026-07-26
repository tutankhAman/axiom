import React from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import type { Summary } from "@/types"

function formatKwh(kwh: number): string {
  return `${kwh.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`
}

function savingsColor(pct: number): string {
  if (pct <= 0) return "text-red-500"
  if (pct > 20) return "text-emerald-500"
  return "text-amber-500"
}

interface MetricCardProps {
  label: string
  value: string
  subtext?: string
  highlight?: string
}

function MetricCard({ label, value, subtext, highlight }: MetricCardProps) {
  return (
    <Card>
      <CardContent className="p-5">
        <p className="text-xs font-medium text-muted-foreground tracking-wide uppercase mb-1">
          {label}
        </p>
        <p className={`text-2xl font-semibold tracking-tight ${highlight || ""}`}>
          {value}
          {subtext && (
            <span className="text-xs font-normal text-muted-foreground ml-2">
              {subtext}
            </span>
          )}
        </p>
      </CardContent>
    </Card>
  )
}

const SummaryCards = React.memo(function SummaryCards({ summary }: { summary: Summary }) {
  const savingsPct = summary.pct_savings.toFixed(1)
  const isNegative = summary.pct_savings <= 0

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <MetricCard
        label="Baseline Energy"
        value={formatKwh(summary.baseline_kwh)}
        subtext="kWh"
      />
      <MetricCard
        label="Closed-Loop Energy"
        value={formatKwh(summary.closed_loop_kwh)}
        subtext="kWh"
      />
      <Card>
        <CardContent className="p-5">
          <p className="text-xs font-medium text-muted-foreground tracking-wide uppercase mb-1">
            Energy Savings
          </p>
          <p className={`text-3xl font-bold tracking-tight ${savingsColor(summary.pct_savings)}`}>
            {isNegative ? "" : "+"}{savingsPct}%
          </p>
        </CardContent>
      </Card>
      <MetricCard
        label="Comfort Compliance"
        value={`${summary.comfort_compliance_pct_closed_loop.toFixed(1)}%`}
        subtext={`vs ${summary.comfort_compliance_pct_baseline.toFixed(1)}%`}
      />
      <Separator className="col-span-2 lg:col-span-4" />
    </div>
  )
})

export default SummaryCards