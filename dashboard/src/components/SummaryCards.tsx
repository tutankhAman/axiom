import React from "react"
import { Card, CardContent } from "@/components/ui/card"
import type { Summary } from "@/types"

const formatter = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

function savingsVariant(pct: number): "destructive" | "warning" | "success" {
  if (pct <= 0) return "destructive"
  if (pct < 15) return "warning"
  return "success"
}

function savingsSymbol(pct: number): string {
  if (pct > 0) return "+"
  return ""
}

interface MetricCardGroupProps {
  title: string
  primary: { value: string; unit?: string }
  secondary?: string
  accent?: boolean
  variant?: "default" | "success" | "warning" | "destructive"
}

function MetricCardGroup({ title, primary, secondary, accent, variant = "default" }: MetricCardGroupProps) {
  const accentClass = variant === "success"
    ? "text-success"
    : variant === "warning"
    ? "text-warning"
    : variant === "destructive"
    ? "text-destructive"
    : "text-foreground"

  return (
    <Card className="group transition-colors duration-300 hover:border-primary/30">
      <CardContent className="p-5">
        <p className="text-[10px] font-medium tracking-[0.18em] uppercase text-muted-foreground mb-2.5">
          {title}
        </p>
        <div className="flex items-baseline gap-2">
          <span className={`text-[1.75rem] font-bold leading-none tracking-tight tabular-nums ${accent ? accentClass : "text-foreground"}`}>
            {primary.value}
          </span>
          {primary.unit && (
            <span className="text-sm font-medium text-muted-foreground">
              {primary.unit}
            </span>
          )}
        </div>
        {secondary && (
          <p className="mt-2 text-[11px] font-mono text-muted-foreground tabular-nums">
            {secondary}
          </p>
        )}
      </CardContent>
    </Card>
  )
}

const SummaryCards = React.memo(function SummaryCards({ summary }: { summary: Summary }) {
  const pct = summary.pct_savings.toFixed(1)

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <div className="animate-fade-in-up animate-stagger-1">
        <MetricCardGroup
          title="Baseline Energy"
          primary={{ value: formatter.format(summary.baseline_kwh), unit: "kWh" }}
        />
      </div>
      <div className="animate-fade-in-up animate-stagger-2">
        <MetricCardGroup
          title="Closed-Loop Energy"
          primary={{ value: formatter.format(summary.closed_loop_kwh), unit: "kWh" }}
        />
      </div>
      <div className="animate-fade-in-up animate-stagger-3">
        <MetricCardGroup
          title="Energy Savings"
          primary={{ value: `${savingsSymbol(summary.pct_savings)}${pct}%` }}
          accent
          variant={savingsVariant(summary.pct_savings)}
        />
      </div>
      <div className="animate-fade-in-up animate-stagger-4">
        <MetricCardGroup
          title="Comfort Compliance"
          primary={{ value: `${summary.comfort_compliance_pct_closed_loop.toFixed(1)}%` }}
          secondary={`baseline ${summary.comfort_compliance_pct_baseline.toFixed(1)}%`}
          variant={summary.comfort_compliance_pct_closed_loop >= 90 ? "success" : "warning"}
        />
      </div>
    </div>
  )
})

export default SummaryCards
