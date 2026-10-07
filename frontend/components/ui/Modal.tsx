"use client"

import { useEffect, useRef } from "react"
import type { ReactNode } from "react"

import { cn } from "@/lib/cn"

interface ModalProps {
  open: boolean
  onClose: () => void
  // false while something is running: Escape and a click on the backdrop then do nothing
  dismissable?: boolean
  labelledBy: string // the id of the element that holds the title
  wide?: boolean
  children: ReactNode
}

// A modal built on the native <dialog>: the browser traps focus inside it, closes it on Escape
// and makes the rest of the page inert, which is hard to get right by hand.
export function Modal({ open, onClose, dismissable = true, labelledBy, wide = false, children }: ModalProps) {
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
      className={cn(
        "max-h-[85dvh] rounded-card border border-line bg-surface p-6 text-ink shadow-card backdrop:bg-black/50",
        wide ? "w-[min(44rem,calc(100vw-2rem))]" : "w-[min(28rem,calc(100vw-2rem))]",
      )}
      aria-labelledby={labelledBy}
      onCancel={(event) => {
        event.preventDefault() // Escape: let React state decide, so the two never disagree
        if (dismissable) onClose()
      }}
      onClick={(event) => {
        if (event.target === ref.current && dismissable) onClose() // a click on the dimmed backdrop
      }}
    >
      {children}
    </dialog>
  )
}
