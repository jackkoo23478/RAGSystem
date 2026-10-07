const NO_VALUE = "–"

// 850 -> "850 ms", 6028 -> "6.0 s"
export function formatLatency(ms: number | null): string {
  if (ms === null) return NO_VALUE
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`
}

// 0.3384 -> "34%"
export function formatPercent(rate: number | null): string {
  if (rate === null) return NO_VALUE
  return `${Math.round(rate * 100)}%`
}

// "2026-10-07" -> "7 Oct". The day is a UTC day from the backend, so it is read as one:
// going through the local timezone could show the neighbouring day.
export function formatDay(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number)
  const date = new Date(Date.UTC(year, month - 1, day))
  if (Number.isNaN(date.getTime())) return ""
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" })
}
