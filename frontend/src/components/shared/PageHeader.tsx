import * as React from "react"
import { cn } from "@/lib/utils"

interface PageHeaderProps {
  eyebrow?: string
  title: string
  subtitle?: string
  children?: React.ReactNode
  className?: string
}

export function PageHeader({ eyebrow, title, subtitle, children, className }: PageHeaderProps) {
  return (
    <div className={cn("flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-6", className)}>
      <div className="flex flex-col">
        {eyebrow && (
          <span className="mb-2 text-[10px] font-bold uppercase tracking-[2px] text-green flex items-center gap-2 before:content-[''] before:w-5 before:h-0.5 before:bg-green/50">
            {eyebrow}
          </span>
        )}
        <h1 className="text-3xl md:text-4xl font-semibold -tracking-[1.3px] text-[var(--ink)]">
          {title}
        </h1>
        {subtitle && (
          <p className="mt-1 text-[var(--muted)]">
            {subtitle}
          </p>
        )}
      </div>
      {children && (
        <div className="flex items-center shrink-0">
          {children}
        </div>
      )}
    </div>
  )
}
