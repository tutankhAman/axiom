import React from "react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import type { DecisionEntry } from "@/types"

interface DecisionLogProps {
  decisions: DecisionEntry[]
}

function strategyBadge(hourOfDay: number): string {
  if (6 <= hourOfDay && hourOfDay < 7) return "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
  if (7 <= hourOfDay && hourOfDay < 14) return "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300"
  if (14 <= hourOfDay && hourOfDay < 19) return "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300"
  return "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300"
}

function strategyLabel(hourOfDay: number): string {
  if (6 <= hourOfDay && hourOfDay < 7) return "pre-cool"
  if (7 <= hourOfDay && hourOfDay < 14) return "occupied"
  if (14 <= hourOfDay && hourOfDay < 19) return "peak"
  return "setback"
}

const DecisionLog = React.memo(function DecisionLog({ decisions }: DecisionLogProps) {
  return (
    <div className="border bg-card overflow-hidden">
      <div className="px-6 py-5 border-b">
        <h3 className="text-base font-semibold text-foreground tracking-tight">
          Agent Decision Log
        </h3>
      </div>
      <ScrollArea className="h-[500px] w-full">
        <div className="w-full">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[60px] font-semibold text-sm text-foreground">Day</TableHead>
                <TableHead className="w-[56px] font-semibold text-sm text-foreground">Hour</TableHead>
                <TableHead className="w-[80px] font-semibold text-sm text-foreground">Strategy</TableHead>
                <TableHead className="w-[80px] font-semibold text-sm text-foreground">Zone</TableHead>
                <TableHead className="w-[80px] font-semibold text-sm text-foreground">Setpoint</TableHead>
                <TableHead className="font-semibold text-sm text-foreground">Reason</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[...decisions].reverse().map((d) => (
                <TableRow key={`${d.day}-${d.hour_of_day}-${d.zone}`}>
                  <TableCell className="font-mono text-sm tabular-nums">{d.day}</TableCell>
                  <TableCell className="font-mono text-sm tabular-nums">{d.hour_of_day}:00</TableCell>
                  <TableCell>
                    <Badge className={`text-xs font-medium ${strategyBadge(d.hour_of_day)}`}>
                      {strategyLabel(d.hour_of_day)}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-sm">{d.zone}</TableCell>
                  <TableCell className="font-mono text-sm tabular-nums">
                    {d.cooling_c}°C
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground max-w-[320px] truncate" title={d.reason}>
                    {d.reason}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </ScrollArea>
      <Separator />
    </div>
  )
})

export default DecisionLog