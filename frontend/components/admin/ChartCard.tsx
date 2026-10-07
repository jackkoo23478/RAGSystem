"use client"

import { useId } from "react"
import type { ReactNode } from "react"

import { cn } from "@/lib/cn"

interface ChartCardProps {
  title: string
  description: string
  // while new data loads, the old chart stays on screen, a little faded, so nothing jumps
  refreshing?: boolean
  table: ReactNode // the same numbers as the chart: a chart must never be the only way to read them
  children: ReactNode
}

export function ChartCard({ title, description, refreshing = false, table, children }: ChartCardProps) {
  const headingId = useId()

  return (
    <section className="min-w-0 rounded-card border border-line bg-surface p-5 shadow-card" aria-labelledby={headingId}>
      <h2 id={headingId} className="text-base font-semibold">
        {title}
      </h2>
      <p className="text-sm text-muted">{description}</p>

      <div className={cn("mt-4 transition-opacity duration-150", refreshing && "opacity-50")}>{children}</div>

      <details className="mt-3 text-sm">
        <summary className="cursor-pointer text-muted">View as table</summary>
        <div className="mt-2 max-h-64 overflow-auto">{table}</div>
      </details>
    </section>
  )
}
