import type { ButtonHTMLAttributes } from "react"

import styles from "./button.module.css"

type Variant = "primary" | "secondary" | "ghost"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  fullWidth?: boolean
}

export function Button({ variant = "secondary", fullWidth = false, className, type = "button", ...rest }: ButtonProps) {
  const classes = [styles.button, styles[variant], fullWidth ? styles.full : "", className ?? ""]
    .filter(Boolean)
    .join(" ")

  return <button type={type} className={classes} {...rest} />
}
