import { formatTime } from "@/lib/format/time"
import type { QueryHistoryItem, QueryStatus } from "@/lib/types/rag"

import styles from "./history.module.css"

// short note shown next to a question that did not get an answer
function statusNote(status: QueryStatus): string {
  switch (status) {
    case "answered":
      return ""
    case "no_evidence":
      return " · no sources found"
    case "invalid_answer":
      return " · no reliable answer"
    case "failed":
      return " · error"
  }
}

interface HistoryListProps {
  items: QueryHistoryItem[]
  selectedId: number | null
  disabled: boolean
  error: string | null
  onSelect: (id: number) => void
}

export function HistoryList({ items, selectedId, disabled, error, onSelect }: HistoryListProps) {
  if (error) return <p role="alert" className={styles.notice}>{error}</p>
  if (items.length === 0) return <p className={styles.notice}>No questions yet.</p>

  return (
    <ul className={styles.list} aria-label="Question history">
      {items.map((item) => (
        <li key={item.id}>
          <button
            type="button"
            className={item.id === selectedId ? `${styles.item} ${styles.selected}` : styles.item}
            aria-current={item.id === selectedId ? "true" : undefined}
            disabled={disabled}
            onClick={() => onSelect(item.id)}
          >
            <span className={styles.question}>{item.question}</span>
            <span className={styles.meta}>
              {formatTime(item.created_at)}
              {statusNote(item.status)}
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}
