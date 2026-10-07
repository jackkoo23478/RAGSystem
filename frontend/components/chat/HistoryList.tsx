import { cn } from "@/lib/cn"
import { formatTime } from "@/lib/format/time"
import type { QueryHistoryItem, QueryStatus } from "@/lib/types/rag"

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
  if (error) return <p role="alert" className="text-sm text-muted">{error}</p>
  if (items.length === 0) return <p className="text-sm text-muted">No questions yet.</p>

  return (
    <ul className="flex flex-col gap-[0.15rem]" aria-label="Question history">
      {items.map((item) => (
        <li key={item.id}>
          <button
            type="button"
            className={cn(
              "flex w-full cursor-pointer flex-col gap-[0.1rem] rounded-control border border-transparent px-[0.7rem] py-[0.55rem] text-left text-ink transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-55",
              item.id === selectedId ? "bg-accent-soft" : "bg-transparent enabled:hover:bg-surface-2",
            )}
            aria-current={item.id === selectedId ? "true" : undefined}
            disabled={disabled}
            onClick={() => onSelect(item.id)}
          >
            <span className="truncate text-[0.9rem]">{item.question}</span>
            <span className="text-xs text-muted">
              {formatTime(item.created_at)}
              {statusNote(item.status)}
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}
