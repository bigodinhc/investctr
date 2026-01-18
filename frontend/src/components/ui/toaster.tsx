"use client"

import { useToast } from "@/components/ui/use-toast"
import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
} from "@/components/ui/toast"

// Toast duration configuration (in ms)
// Normal: 5000ms, Errors: 8000ms, With action: 10000ms
const DEFAULT_DURATION = 5000
const ERROR_DURATION = 8000
const ACTION_DURATION = 10000

export function Toaster() {
  const { toasts } = useToast()

  return (
    <ToastProvider duration={DEFAULT_DURATION}>
      {toasts.map(function ({ id, title, description, action, variant, duration, ...props }) {
        // Determine duration based on variant and action
        const toastDuration = duration ?? (
          action ? ACTION_DURATION :
          variant === "destructive" ? ERROR_DURATION :
          DEFAULT_DURATION
        )

        return (
          <Toast key={id} variant={variant} duration={toastDuration} {...props}>
            <div className="grid gap-1">
              {title && <ToastTitle>{title}</ToastTitle>}
              {description && (
                <ToastDescription>{description}</ToastDescription>
              )}
            </div>
            {action}
            <ToastClose aria-label="Fechar notificação" />
          </Toast>
        )
      })}
      <ToastViewport />
    </ToastProvider>
  )
}
