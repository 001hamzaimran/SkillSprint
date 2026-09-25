import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] uppercase font-bold tracking-wider transition-colors",
  {
    variants: {
      variant: {
        default: "bg-[var(--border)] text-[var(--ink)]",
        warning: "bg-[var(--amber)]/20 text-[var(--amber)]",
        success: "bg-[var(--lime)] text-[var(--green)]",
        destructive: "bg-red-50 text-red-700",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
