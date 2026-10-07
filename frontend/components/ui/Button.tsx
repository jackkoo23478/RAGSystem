import type { ButtonHTMLAttributes } from "react"

import { cn } from "@/lib/cn"

type Variant = "primary" | "secondary" | "ghost" | "danger"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  fullWidth?: boolean
}

const BASE =
  "inline-flex min-h-10 cursor-pointer items-center justify-center gap-2 rounded-control border border-transparent px-4 font-medium whitespace-nowrap transition-[background-color,border-color,opacity] duration-150 disabled:cursor-not-allowed disabled:opacity-50"

// the hover colours only apply to an enabled button
const VARIANTS: Record<Variant, string> = {
  primary: "bg-accent text-accent-fg enabled:hover:bg-accent-hover",
  secondary: "border-line bg-surface text-ink enabled:hover:bg-surface-2",
  ghost: "bg-transparent text-ink enabled:hover:bg-surface-2",
  // a destructive action reads differently from a normal one
  danger: "bg-danger text-surface enabled:hover:brightness-[0.92]",
}

export function Button({ variant = "secondary", fullWidth = false, className, type = "button", ...rest }: ButtonProps) {
  return <button type={type} className={cn(BASE, VARIANTS[variant], fullWidth && "w-full", className)} {...rest} />
}
