"use client"

import { cn } from "@/lib/cn"

interface RangeFilterProps {
  options: readonly number[] // numbers of days
  value: number
  onChange: (days: number) => void
}

// presets only: nobody wants a calendar for "the last 30 days"
export function RangeFilter({ options, value, onChange }: RangeFilterProps) {
  return (
    <div role="group" aria-label="Time range" className="inline-flex rounded-control border border-line bg-surface p-[2px]">
      {options.map((days) => (
        <button
          key={days}
          type="button"
          aria-pressed={days === value}
          onClick={() => onChange(days)}
          className={cn(
            "cursor-pointer rounded-[6px] px-3 py-[0.2rem] text-sm font-medium transition-colors duration-150",
            days === value ? "bg-accent-soft text-accent" : "text-muted hover:bg-surface-2",
          )}
        >
          {days} days
        </button>
      ))}
    </div>
  )
}
