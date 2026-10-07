import type { QueryStatus } from "@/lib/types/rag"

import { BADGE_BASE, BADGE_TONES } from "./badge"

const LABELS: Record<QueryStatus, string> = {
  answered: "Answered",
  no_evidence: "No sources",
  invalid_answer: "Unreliable",
  failed: "Error",
}

const TONES: Record<QueryStatus, string> = {
  answered: BADGE_TONES.success,
  no_evidence: BADGE_TONES.neutral,
  invalid_answer: BADGE_TONES.warning,
  failed: BADGE_TONES.danger,
}

// the label always carries the meaning; the colour only backs it up
export function QueryStatusBadge({ status }: { status: string }) {
  const known = status in LABELS
  const label = known ? LABELS[status as QueryStatus] : status
  const tone = known ? TONES[status as QueryStatus] : BADGE_TONES.neutral
  return <span className={`${BADGE_BASE} ${tone}`}>{label}</span>
}
