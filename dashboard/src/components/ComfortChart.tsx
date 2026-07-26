import React from "react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceArea,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  ChartContainer,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendItem,
} from "@/components/ui/chart"
import type { PivotPoint } from "@/types"

const BASELINE_COLOR = "oklch(0.45 0.01 260)"
const AGENT_COLOR = "oklch(0.55 0.15 220)"

interface ComfortChartProps {
  data: PivotPoint[]
}

const ComfortChart = React.memo(function ComfortChart({ data }: ComfortChartProps) {
  return (
    <Card className="animate-fade-in-up animate-stagger-6">
      <CardHeader className="pb-2">
        <CardTitle>Thermal Comfort (PMV)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ChartContainer
            config={{
              baseline: { label: "Baseline PMV", color: BASELINE_COLOR },
              agent: { label: "Agent PMV", color: AGENT_COLOR },
            }}
            className="h-full w-full"
          >
            <LineChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: 0 }}>
              <CartesianGrid
                strokeDasharray="2 4"
                className="stroke-border"
                vertical={false}
              />
              <XAxis
                dataKey="hour"
                tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${Number(v).toFixed(0)}h`}
                type="number"
                domain={["dataMin", "dataMax"]}
                tickCount={8}
                minTickGap={24}
                className="text-muted-foreground"
              />
              <YAxis
                tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                tickLine={false}
                axisLine={false}
                domain={[-1, 1]}
                width={32}
                className="text-muted-foreground"
              />
              <Tooltip
                content={
                  <ChartTooltipContent
                    formatter={(v) => [Number(v).toFixed(3), ""]}
                  />
                }
              />
              <Legend content={<ChartLegend />}>
                <ChartLegendItem color={BASELINE_COLOR} label="Baseline PMV" />
                <ChartLegendItem color={AGENT_COLOR} label="Agent PMV" />
              </Legend>
              <ReferenceArea
                y1={-0.5}
                y2={0.5}
                fill="oklch(0.5 0.14 160 / 0.12)"
                stroke="oklch(0.5 0.14 160 / 0.3)"
                strokeDasharray="4 4"
                strokeWidth={0.5}
              />
              <ReferenceArea
                y1={-1}
                y2={-0.5}
                fill="oklch(0.52 0.22 25 / 0.06)"
                stroke="oklch(0.52 0.22 25 / 0.15)"
                strokeDasharray="4 4"
                strokeWidth={0.5}
              />
              <ReferenceArea
                y1={0.5}
                y2={1}
                fill="oklch(0.52 0.22 25 / 0.06)"
                stroke="oklch(0.52 0.22 25 / 0.15)"
                strokeDasharray="4 4"
                strokeWidth={0.5}
              />
              <Line
                type="monotone"
                dataKey="baseline_pmv"
                stroke={BASELINE_COLOR}
                strokeWidth={1.25}
                dot={false}
                activeDot={{ r: 3, fill: BASELINE_COLOR }}
              />
              <Line
                type="monotone"
                dataKey="agent_pmv"
                stroke={AGENT_COLOR}
                strokeWidth={1.25}
                dot={false}
                activeDot={{ r: 3, fill: AGENT_COLOR }}
              />
            </LineChart>
          </ChartContainer>
        </div>
      </CardContent>
    </Card>
  )
})

export default ComfortChart
