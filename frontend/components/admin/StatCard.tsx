interface StatCardProps {
  label: string
  value: string
  note?: string
}

// A single number is shown as a number, not as a one-bar chart. Meant to sit inside a <dl>.
// Proportional digits (no tabular-nums): the value is large and stands alone.
export function StatCard({ label, value, note }: StatCardProps) {
  return (
    <div className="rounded-card border border-line bg-surface p-5 shadow-card">
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="mt-1 text-3xl font-semibold">{value}</dd>
      {note && <dd className="mt-1 text-sm text-muted">{note}</dd>}
    </div>
  )
}
