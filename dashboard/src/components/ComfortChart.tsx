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

interface ComfortChartProps {
  data: PivotPoint[]
}

const ComfortChart = React.memo(function ComfortChart({ data }: ComfortChartProps) {
  return (
    <Card className="col-span-1 lg:col-span-2">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground tracking-wide uppercase">
          Thermal Comfort (PMV)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ChartContainer
            config={{
              baseline: {
                label: "Baseline PMV",
                color: "hsl(0 0% 60%)",
              },
              agent: {
                label: "Agent PMV",
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
                domain={[-1, 1]}
                width={36}
              />
              <Tooltip
                content={<ChartTooltipContent formatter={(v) => [Number(v).toFixed(3), ""]} />}
              />
              <Legend content={<ChartLegend />}>
                <ChartLegendItem color="hsl(0 0% 60%)" label="Baseline PMV" />
                <ChartLegendItem color="hsl(221.2 83.2% 53.3%)" label="Agent PMV" />
              </Legend>
              <ReferenceArea
                y1={-0.5}
                y2={0.5}
                fill="hsl(142 76% 36% / 0.08)"
                strokeDasharray=""
              />
              <ReferenceArea
                y1={-1}
                y2={-0.5}
                fill="hsl(0 72% 51% / 0.04)"
                strokeDasharray=""
              />
              <ReferenceArea
                y1={0.5}
                y2={1}
                fill="hsl(0 72% 51% / 0.04)"
                strokeDasharray=""
              />
              <Line
                type="monotone"
                dataKey="baseline_pmv"
                stroke="#9ca3af"
                strokeWidth={1.5}
                dot={false}
                activeDot={{ r: 3, fill: "#9ca3af" }}
              />
              <Line
                type="monotone"
                dataKey="agent_pmv"
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

export default ComfortChart