import * as React from "react"
import { ResponsiveContainer } from "recharts"
import { cn } from "@/lib/utils"

interface ChartConfig {
  label?: string
  color?: string
}

const ChartContext = React.createContext<{ config: Record<string, ChartConfig> }>(
  { config: {} }
)

const ChartContainer = React.forwardRef<
  HTMLDivElement,
  React.ComponentProps<"div"> & {
    config: Record<string, ChartConfig>
  }
>(({ className, children, config, ...props }, ref) => (
  <ChartContext.Provider value={{ config }}>
    <div
      ref={ref}
      className={cn(
        "flex aspect-video justify-center text-xs",
        "[&_.recharts-cartesian-axis-tick_text]:fill-muted-foreground",
        "[&_.recharts-cartesian-grid_line[stroke]]:stroke-border/50",
        "[&_.recharts-surface]:outline-none",
        className
      )}
      {...props}
    >
      <ResponsiveContainer width="100%" height="100%">
        {children as React.ReactElement}
      </ResponsiveContainer>
    </div>
  </ChartContext.Provider>
))
ChartContainer.displayName = "ChartContainer"

interface ChartTooltipContentProps
  extends React.HTMLAttributes<HTMLDivElement> {
  active?: boolean
  payload?: Array<{ name?: string; value?: number | string; color?: string; dataKey?: string }>
  label?: string | number
  labelFormatter?: (label: string | number) => string
  formatter?: (value: number | string, name: string) => [string, string]
  hideLabel?: boolean
  hideIndicator?: boolean
  indicator?: "dot" | "line" | "dashed"
}

const ChartTooltipContent = React.forwardRef<
  HTMLDivElement,
  ChartTooltipContentProps
>(
  (
    {
      className,
      active,
      payload,
      label,
      labelFormatter,
      formatter,
      hideLabel = false,
      hideIndicator = false,
      indicator = "dot",
    },
    ref
  ) => {
    if (!active || !payload?.length) return null

    return (
      <div
        ref={ref}
        className={cn(
          "grid gap-1 p-3 bg-popover text-popover-foreground border border-border rounded-lg shadow-lg min-w-[8rem]",
          className
        )}
      >
        {!hideLabel && label != null && (
          <div className="text-xs font-medium text-foreground mb-1">
            {labelFormatter ? labelFormatter(label) : `Hour ${label}`}
          </div>
        )}
        <div className="grid gap-1.5">
          {payload.map((item, index) => {
            const formatted = formatter
              ? formatter(item.value as number, item.name ?? "")
              : [item.value, item.name]

            return (
              <div key={index} className="flex items-center gap-2">
                {!hideIndicator && item.color && (
                  <div
                    className={cn(
                      "rounded-full shrink-0",
                      indicator === "dot" && "w-2 h-2",
                      indicator === "line" && "w-4 h-0.5",
                      indicator === "dashed" &&
                        "w-4 h-0.5 border-t-[2px] border-dashed"
                    )}
                    style={{ backgroundColor: item.color }}
                  />
                )}
                <span className="text-xs text-muted-foreground font-medium flex-1">
                  {formatted[1]}
                </span>
                <span className="text-xs font-semibold text-foreground tabular-nums">
                  {formatted[0]}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    )
  }
)
ChartTooltipContent.displayName = "ChartTooltipContent"

const ChartLegend = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className }, ref) => (
  <div
    ref={ref}
    className={cn(
      "flex flex-wrap items-center gap-4 text-xs text-muted-foreground",
      className
    )}
  />
))
ChartLegend.displayName = "ChartLegend"

interface ChartLegendItemProps extends React.HTMLAttributes<HTMLDivElement> {
  color?: string
  label: string
}

const ChartLegendItem = React.forwardRef<HTMLDivElement, ChartLegendItemProps>(
  ({ className, color, label, ...props }, ref) => (
    <div ref={ref} className={cn("flex items-center gap-1.5", className)} {...props}>
      {color && (
        <div
          className="h-2 w-2 rounded-full shrink-0"
          style={{ backgroundColor: color }}
        />
      )}
      <span>{label}</span>
    </div>
  )
)
ChartLegendItem.displayName = "ChartLegendItem"

export {
  ChartContainer,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendItem,
}