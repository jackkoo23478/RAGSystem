// The backend sends UTC timestamps without a timezone suffix ("2026-10-06T05:13:10.236492").
// `new Date()` would read that as local time and show the wrong hour, so mark it as UTC first.
export function formatTime(iso: string): string {
  const hasTimezone = /(Z|[+-]\d{2}:\d{2})$/.test(iso)
  const date = new Date(hasTimezone ? iso : `${iso}Z`)
  if (Number.isNaN(date.getTime())) return ""
  // fixed locale so the interface does not mix languages; the hour is still the user's own timezone
  return date.toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })
}
