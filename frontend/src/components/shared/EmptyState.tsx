import * as React from "react"
import { cn } from "@/lib/utils"

interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center text-center p-8", className)}>
      {icon && (
        <div className="mb-4 text-[var(--muted)]">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-semibold text-[var(--ink)] mb-1">
        {title}
      </h3>
      {description && (
        <p className="text-sm text-[var(--muted)] mb-6 max-w-sm">
          {description}
        </p>
      )}
      {action && (
        <div>
          {action}
        </div>
      )}
    </div>
  )
}
