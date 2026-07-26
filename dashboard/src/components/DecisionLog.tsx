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

export default function DecisionLog({ decisions }: DecisionLogProps) {
  return (
    <div className="rounded-xl border bg-card">
      <div className="px-5 py-4 border-b">
        <h3 className="text-sm font-medium text-muted-foreground tracking-wide uppercase">
          Agent Decision Log
        </h3>
      </div>
      <ScrollArea className="max-h-[400px]">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[60px]">Day</TableHead>
              <TableHead className="w-[56px]">Hour</TableHead>
              <TableHead className="w-[80px]">Strategy</TableHead>
              <TableHead className="w-[80px]">Zone</TableHead>
              <TableHead className="w-[80px]">Setpoint</TableHead>
              <TableHead>Reason</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {decisions.map((d, i) => (
              <TableRow key={i}>
                <TableCell className="font-mono text-xs tabular-nums">{d.day}</TableCell>
                <TableCell className="font-mono text-xs tabular-nums">{d.hour_of_day}:00</TableCell>
                <TableCell>
                  <Badge className={`text-[10px] font-medium ${strategyBadge(d.hour_of_day)}`}>
                    {strategyLabel(d.hour_of_day)}
                  </Badge>
                </TableCell>
                <TableCell className="font-mono text-xs">{d.zone}</TableCell>
                <TableCell className="font-mono text-xs tabular-nums">
                  {d.cooling_c}°C
                </TableCell>
                <TableCell className="text-xs text-muted-foreground max-w-[320px] truncate" title={d.reason}>
                  {d.reason}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </ScrollArea>
      <Separator />
    </div>
  )
}