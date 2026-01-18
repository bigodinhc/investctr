import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-lg border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-vermillion text-white",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground",
        destructive:
          "border-transparent bg-destructive/15 text-destructive",
        success:
          "border-transparent bg-success/15 text-success",
        warning:
          "border-transparent bg-warning/15 text-warning",
        info:
          "border-transparent bg-info/15 text-info",
        vermillion:
          "border-transparent bg-vermillion/15 text-vermillion",
        outline:
          "border-border text-foreground bg-white/5",
        "outline-vermillion":
          "border-vermillion/50 text-vermillion bg-vermillion/5",
        "outline-success":
          "border-success/50 text-success bg-success/5",
        "outline-destructive":
          "border-destructive/50 text-destructive bg-destructive/5",
        // Gold variant (main theme color)
        gold:
          "border-transparent bg-gold/15 text-gold",
        "outline-gold":
          "border-gold/50 text-gold bg-gold/5",
        // Glass variant
        glass:
          "glass-card-subtle border-white/10 text-foreground",
      },
      size: {
        default: "px-2.5 py-0.5 text-xs",
        sm: "px-2 py-0.5 text-[10px]",
        lg: "px-3 py-1 text-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  icon?: React.ReactNode
}

function Badge({ className, variant, size, icon, children, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant, size }), className)} {...props}>
      {icon && <span className="mr-1">{icon}</span>}
      {children}
    </div>
  )
}

export { Badge, badgeVariants }
