import type { DocumentStatus } from "@/lib/types/document"

import styles from "./status-badge.module.css"

const LABELS: Record<DocumentStatus, string> = {
  pending: "Not processed",
  processing: "Processing",
  processed: "Ready",
  failed: "Failed",
  flagged: "Needs review",
}

// the backend keeps the status as free text, so an unknown value must still show something readable
export function StatusBadge({ status }: { status: string }) {
  const known = status in LABELS
  const label = known ? LABELS[status as DocumentStatus] : status
  const tone = known ? styles[status] : styles.pending
  return <span className={`${styles.badge} ${tone}`}>{label}</span>
}
