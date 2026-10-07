import type { DocumentStatus } from "@/lib/types/document"

const LABELS: Record<DocumentStatus, string> = {
  pending: "Not processed",
  processing: "Processing",
  processed: "Ready",
  failed: "Failed",
  flagged: "Needs review",
}

const TONES: Record<DocumentStatus, string> = {
  pending: "bg-surface-2 text-muted",
  processing: "bg-accent-soft text-accent",
  processed: "bg-success-soft text-success",
  failed: "bg-danger-soft text-danger",
  flagged: "bg-warning-soft text-warning",
}

// the backend keeps the status as free text, so an unknown value must still show something readable
export function StatusBadge({ status }: { status: string }) {
  const known = status in LABELS
  const label = known ? LABELS[status as DocumentStatus] : status
  const tone = known ? TONES[status as DocumentStatus] : TONES.pending
  return (
    <span className={`inline-block rounded-full px-[0.6rem] py-[0.1rem] text-[0.8rem] font-medium whitespace-nowrap ${tone}`}>{label}</span>
  )
}
