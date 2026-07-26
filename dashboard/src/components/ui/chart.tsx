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
        "flex justify-center text-xs",
        "[&_.recharts-cartesian-axis-tick_text]:fill-muted-foreground",
        "[&_.recharts-cartesian-grid_line]:stroke-border/50",
        "[&_.recharts-cartesian-grid_line[stroke='']]:stroke-none",
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
          "rounded-md border bg-popover px-3 py-2.5 text-xs shadow-lg",
          "ring-1 ring-white/[0.04] ring-inset",
          className
        )}
      >
        {!hideLabel && label != null && (
          <div className="text-[11px] font-mono font-medium text-primary mb-1.5 pb-1.5 border-b border-border">
            {labelFormatter ? labelFormatter(label) : `Hour ${label}`}
          </div>
        )}
        <div className="grid gap-1">
          {payload.map((item, index) => {
            const formatted = formatter
              ? formatter(item.value as number, item.name ?? "")
              : [item.value, item.name]

            return (
              <div key={index} className="flex items-center gap-2">
                {!hideIndicator && item.color && (
                  <div
                    className={cn(
                      "shrink-0",
                      indicator === "dot" && "w-1.5 h-1.5 rounded-full",
                      indicator === "line" && "w-3 h-px",
                      indicator === "dashed" &&
                        "w-3 h-px border-t border-dashed border-current"
                    )}
                    style={{ backgroundColor: item.color }}
                  />
                )}
                <span className="font-mono text-muted-foreground flex-1 min-w-0 truncate">
                  {formatted[1]}
                </span>
                <span className="font-mono font-semibold text-foreground tabular-nums">
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
      "flex flex-wrap items-center gap-5 mt-4 justify-center",
      "text-[11px] font-mono text-muted-foreground",
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
    <div ref={ref} className={cn("flex items-center gap-2", className)} {...props}>
      {color && (
        <div
          className="h-2.5 w-2.5 rounded-sm shrink-0"
          style={{ backgroundColor: color }}
        />
      )}
      <span className="tabular-nums">{label}</span>
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
