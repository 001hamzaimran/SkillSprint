import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-xl font-semibold transition-colors disabled:opacity-55 disabled:cursor-not-allowed focus-visible:ring-2 focus-visible:ring-green/40 focus-visible:ring-offset-2",
  {
    variants: {
      variant: {
        default: "bg-[var(--green)] text-[var(--paper)] hover:opacity-90",
        secondary: "bg-[var(--white)] border border-[var(--border)] text-[var(--ink)] hover:bg-[var(--paper)]",
        light: "bg-[var(--lime)] text-[var(--ink)] hover:opacity-90",
        ghost: "bg-transparent hover:bg-[var(--paper)] text-[var(--ink)]",
        destructive: "bg-red-600 text-[var(--paper)] hover:bg-red-700",
      },
      size: {
        default: "h-10 px-5",
        sm: "h-8 px-3 text-xs",
        lg: "h-12 px-8",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }
