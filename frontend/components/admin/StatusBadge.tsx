import type { DocumentStatus } from "@/lib/types/document"

import { BADGE_BASE, BADGE_TONES } from "./badge"

const LABELS: Record<DocumentStatus, string> = {
  pending: "Not processed",
  processing: "Processing",
  processed: "Ready",
  failed: "Failed",
  flagged: "Needs review",
}

const TONES: Record<DocumentStatus, string> = {
  pending: BADGE_TONES.neutral,
  processing: BADGE_TONES.accent,
  processed: BADGE_TONES.success,
  failed: BADGE_TONES.danger,
  flagged: BADGE_TONES.warning,
}

// the backend keeps the status as free text, so an unknown value must still show something readable
export function StatusBadge({ status }: { status: string }) {
  const known = status in LABELS
  const label = known ? LABELS[status as DocumentStatus] : status
  const tone = known ? TONES[status as DocumentStatus] : TONES.pending
  return <span className={`${BADGE_BASE} ${tone}`}>{label}</span>
}
