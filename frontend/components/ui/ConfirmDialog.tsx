"use client"

import type { ReactNode } from "react"

import { Button } from "./Button"
import { Modal } from "./Modal"

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
  return (
    <Modal open={open} onClose={onCancel} dismissable={!busy} labelledBy="confirm-dialog-title">
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
    </Modal>
  )
}
