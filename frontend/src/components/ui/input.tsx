import * as React from "react"

import { cn } from "@/lib/utils"

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  isNumeric?: boolean
  error?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  variant?: "default" | "glass"
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, isNumeric, error, leftIcon, rightIcon, variant = "default", ...props }, ref) => {
    const baseClasses = "flex h-10 w-full rounded-xl px-3 py-2 text-sm transition-all duration-200 file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-foreground-dim focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"

    const variantClasses = variant === "glass"
      ? "glass-card-subtle border-white/10 focus-visible:border-vermillion/50 focus-visible:ring-2 focus-visible:ring-vermillion/30"
      : "border border-input bg-background focus-visible:border-vermillion focus-visible:ring-2 focus-visible:ring-vermillion/30"

    const inputClasses = cn(
      baseClasses,
      variantClasses,
      isNumeric && "font-mono tabular-nums text-right",
      error && "border-destructive focus-visible:ring-destructive/30 focus-visible:border-destructive",
      leftIcon && "pl-10",
      rightIcon && "pr-10",
      className
    )

    if (leftIcon || rightIcon) {
      return (
        <div className="relative">
          {leftIcon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground-muted">
              {leftIcon}
            </div>
          )}
          <input
            type={type}
            className={inputClasses}
            ref={ref}
            {...props}
          />
          {rightIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground-muted">
              {rightIcon}
            </div>
          )}
        </div>
      )
    }

    return (
      <input
        type={type}
        className={inputClasses}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
