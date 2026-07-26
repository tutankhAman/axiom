import React from "react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  ChartContainer,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendItem,
} from "@/components/ui/chart"
import type { PowerPoint } from "@/types"

const BASELINE_COLOR = "oklch(0.45 0.01 260)"
const AGENT_COLOR = "oklch(0.55 0.15 220)"

interface PowerChartProps {
  data: PowerPoint[]
}

const PowerChart = React.memo(function PowerChart({ data }: PowerChartProps) {
  return (
    <Card className="animate-fade-in-up animate-stagger-5">
      <CardHeader className="pb-2">
        <CardTitle>HVAC Power Demand</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ChartContainer
            config={{
              baseline: { label: "Baseline", color: BASELINE_COLOR },
              agent: { label: "Closed-Loop Agent", color: AGENT_COLOR },
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
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}kW`}
                width={48}
                className="text-muted-foreground"
              />
              <Tooltip
                content={
                  <ChartTooltipContent
                    formatter={(v) => [
                      `${Number(v).toLocaleString()} W`,
                      "",
                    ]}
                  />
                }
              />
              <Legend content={<ChartLegend />}>
                <ChartLegendItem color={BASELINE_COLOR} label="Baseline" />
                <ChartLegendItem color={AGENT_COLOR} label="Closed-Loop Agent" />
              </Legend>
              <Line
                type="monotone"
                dataKey="baseline_w"
                stroke={BASELINE_COLOR}
                strokeWidth={1.25}
                dot={false}
                activeDot={{ r: 3, fill: BASELINE_COLOR }}
              />
              <Line
                type="monotone"
                dataKey="agent_w"
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

export default PowerChart
