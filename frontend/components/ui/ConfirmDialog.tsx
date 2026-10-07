"use client"

import { useEffect, useRef } from "react"
import type { ReactNode } from "react"

import { Button } from "./Button"
import styles from "./confirm-dialog.module.css"

interface ConfirmDialogProps {
  open: boolean
  title: string
  confirmLabel: string
  tone?: "default" | "danger"
  busy?: boolean
  onConfirm: () => void
  onCancel: () => void
  children: ReactNode
}

// A modal built on the native <dialog>: the browser traps focus inside it, closes it on Escape
// and makes the rest of the page inert, which is hard to get right by hand.
export function ConfirmDialog({
  open,
  title,
  confirmLabel,
  tone = "default",
  busy = false,
  onConfirm,
  onCancel,
  children,
}: ConfirmDialogProps) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={ref}
      className={styles.dialog}
      aria-labelledby="confirm-dialog-title"
      onCancel={(event) => {
        event.preventDefault() // Escape: let React state decide, so the two never disagree
        if (!busy) onCancel()
      }}
      onClick={(event) => {
        if (event.target === ref.current && !busy) onCancel() // a click on the dimmed backdrop
      }}
    >
      <h2 id="confirm-dialog-title" className={styles.title}>
        {title}
      </h2>
      <div className={styles.body}>{children}</div>
      <div className={styles.actions}>
        <Button variant="secondary" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
        <Button variant="primary" className={tone === "danger" ? styles.danger : undefined} onClick={onConfirm} disabled={busy}>
          {busy ? "Working..." : confirmLabel}
        </Button>
      </div>
    </dialog>
  )
}
