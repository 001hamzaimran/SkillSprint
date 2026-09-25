import * as React from "react"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface StatCardProps {
  label: string
  value: string | number
  subtext?: string
  className?: string
}

export function StatCard({ label, value, subtext, className }: StatCardProps) {
  return (
    <Card className={cn("flex flex-col gap-2 p-6", className)}>
      <span className="text-[9px] font-bold uppercase tracking-wider text-[var(--muted)]">
        {label}
      </span>
      <span className="text-4xl font-semibold text-[var(--ink)]">
        {value}
      </span>
      {subtext && (
        <span className="text-xs text-[var(--muted)]">
          {subtext}
        </span>
      )}
    </Card>
  )
}
