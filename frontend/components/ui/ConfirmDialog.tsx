"use client"

import { useEffect, useRef } from "react"
import type { ReactNode } from "react"

import { Button } from "./Button"

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
      className="w-[min(28rem,calc(100vw-2rem))] rounded-card border border-line bg-surface p-6 text-ink shadow-card backdrop:bg-black/50"
      aria-labelledby="confirm-dialog-title"
      onCancel={(event) => {
        event.preventDefault() // Escape: let React state decide, so the two never disagree
        if (!busy) onCancel()
      }}
      onClick={(event) => {
        if (event.target === ref.current && !busy) onCancel() // a click on the dimmed backdrop
      }}
    >
      <h2 id="confirm-dialog-title" className="mb-3 text-[1.15rem] font-bold">
        {title}
      </h2>
      <div className="text-muted [&_p]:mb-3">{children}</div>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
        <Button variant={tone === "danger" ? "danger" : "primary"} onClick={onConfirm} disabled={busy}>
          {busy ? "Working..." : confirmLabel}
        </Button>
      </div>
    </dialog>
  )
}
