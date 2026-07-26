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

interface PowerChartProps {
  data: PowerPoint[]
}

const PowerChart = React.memo(function PowerChart({ data }: PowerChartProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground tracking-wide uppercase">
          HVAC Power Demand
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ChartContainer
            config={{
              baseline: {
                label: "Baseline",
                color: "hsl(0 0% 60%)",
              },
              agent: {
                label: "Closed-Loop Agent",
                color: "hsl(221.2 83.2% 53.3%)",
              },
            }}
            className="h-full w-full"
          >
            <LineChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                className="stroke-muted/30"
                vertical={false}
              />
              <XAxis
                dataKey="hour"
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${Number(v).toFixed(0)}h`}
                type="number"
                domain={["dataMin", "dataMax"]}
                tickCount={7}
                minTickGap={20}
              />
              <YAxis
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}kW`}
                width={48}
              />
              <Tooltip
                content={<ChartTooltipContent formatter={(v, name) => [`${Number(v).toLocaleString()} W`, name]} />}
              />
              <Legend content={
                <ChartLegend>
                  <ChartLegendItem color="hsl(0 0% 60%)" label="Baseline" />
                  <ChartLegendItem color="hsl(221.2 83.2% 53.3%)" label="Closed-Loop Agent" />
                </ChartLegend>
              } />
              <Line
                type="monotone"
                name="Baseline"
                dataKey="baseline_w"
                stroke="#9ca3af"
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 3, fill: "#9ca3af" }}
              />
              <Line
                type="monotone"
                name="Closed-Loop Agent"
                dataKey="agent_w"
                stroke="hsl(221.2 83.2% 53.3%)"
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 3, fill: "hsl(221.2 83.2% 53.3%)" }}
              />
            </LineChart>
          </ChartContainer>
        </div>
      </CardContent>
    </Card>
  )
})

export default PowerChart