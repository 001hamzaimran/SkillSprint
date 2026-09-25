import * as React from "react"

import { cn } from "@/lib/utils"

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, ...props }, ref) => {
    return (
      <div className="relative">
        <select
          className={cn(
            "flex h-10 w-full appearance-none rounded-[7px] border border-[var(--border)] bg-[var(--white)] px-3 py-2 text-sm text-[var(--ink)] ring-offset-[var(--paper)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--green)] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
            className
          )}
          ref={ref}
          {...props}
        />
        <div className="pointer-events-none absolute inset-y-0 right-3 flex items-center">
          <svg className="h-4 w-4 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>
    )
  }
)
Select.displayName = "Select"

export { Select }
