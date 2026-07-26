import React from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { DecisionEntry } from "@/types"

interface DecisionLogProps {
  decisions: DecisionEntry[]
}

type Strategy = "pre-cool" | "occupied" | "peak" | "setback"
type StrategyVariant = "default" | "success" | "warning" | "secondary"

function classifyStrategy(hourOfDay: number): { label: Strategy; variant: StrategyVariant } {
  if (6 <= hourOfDay && hourOfDay < 7) return { label: "pre-cool", variant: "default" }
  if (7 <= hourOfDay && hourOfDay < 14) return { label: "occupied", variant: "success" }
  if (14 <= hourOfDay && hourOfDay < 19) return { label: "peak", variant: "warning" }
  return { label: "setback", variant: "secondary" }
}

const DecisionLog = React.memo(function DecisionLog({ decisions }: DecisionLogProps) {
  return (
    <div className="rounded-lg border bg-card overflow-hidden animate-fade-in-up animate-stagger-6">
      <div className="px-6 py-4 border-b flex items-center justify-between">
        <h3 className="text-[11px] font-semibold tracking-[0.2em] uppercase text-muted-foreground">
          Agent Decision Log
        </h3>
        <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
          {decisions.length.toLocaleString()} events
        </span>
      </div>
      <ScrollArea className="h-[480px] w-full">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent border-b border-border/50">
              <TableHead className="w-[52px] font-mono text-[10px] tracking-wider uppercase text-muted-foreground">
                Day
              </TableHead>
              <TableHead className="w-[52px] font-mono text-[10px] tracking-wider uppercase text-muted-foreground">
                Hour
              </TableHead>
              <TableHead className="w-[80px] font-mono text-[10px] tracking-wider uppercase text-muted-foreground">
                Strategy
              </TableHead>
              <TableHead className="w-[60px] font-mono text-[10px] tracking-wider uppercase text-muted-foreground">
                Zone
              </TableHead>
              <TableHead className="w-[72px] font-mono text-[10px] tracking-wider uppercase text-muted-foreground">
                Setpoint
              </TableHead>
              <TableHead className="font-mono text-[10px] tracking-wider uppercase text-muted-foreground">
                Reason
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {[...decisions].reverse().map((d) => {
              const strategy = classifyStrategy(d.hour_of_day)
              return (
                <TableRow
                  key={`${d.day}-${d.hour_of_day}-${d.zone}`}
                  className="group transition-colors hover:bg-primary/[0.03]"
                >
                  <TableCell className="font-mono text-xs tabular-nums py-2.5">
                    {d.day}
                  </TableCell>
                  <TableCell className="font-mono text-xs tabular-nums py-2.5 text-foreground">
                    {String(d.hour_of_day).padStart(2, "0")}:00
                  </TableCell>
                  <TableCell className="py-2.5">
                    <Badge variant={strategy.variant} size="sm">
                      {strategy.label}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs tabular-nums py-2.5">
                    {d.zone}
                  </TableCell>
                  <TableCell className="font-mono text-xs tabular-nums py-2.5 font-medium text-foreground">
                    {d.cooling_c.toFixed(1)}°C
                  </TableCell>
                  <TableCell
                    className="text-xs py-2.5 text-muted-foreground max-w-[360px] truncate"
                    title={d.reason}
                  >
                    {d.reason}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </ScrollArea>
    </div>
  )
})

export default DecisionLog
