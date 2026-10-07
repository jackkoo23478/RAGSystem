import { FileText, Play, RefreshCw, ShieldAlert, Trash2 } from "lucide-react"
import type { ReactNode } from "react"

import { Button } from "@/components/ui/Button"
import { formatTime } from "@/lib/format/time"
import type { DocumentItem } from "@/lib/types/document"

import { StatusBadge } from "./StatusBadge"

interface DocumentTableProps {
  documents: DocumentItem[]
  busyIds: ReadonlySet<number>
  onProcess: (document: DocumentItem) => void
  onReview: (document: DocumentItem) => void
  onDelete: (document: DocumentItem) => void
}

const HEADER_CELL = "border-b border-line px-4 py-3 text-left text-xs font-semibold tracking-wider text-muted uppercase"

// On a narrow screen each row becomes a small card (every table part turns into a block),
// so nothing needs sideways scrolling.
const CELL = "border-b border-line px-4 py-[0.6rem] align-middle max-sm:block max-sm:border-none max-sm:px-0 max-sm:py-[0.15rem]"

// the one action that moves a document forward, which depends on where it is
function mainAction(document: DocumentItem, onProcess: (d: DocumentItem) => void, onReview: (d: DocumentItem) => void, disabled: boolean): ReactNode {
  switch (document.status) {
    case "pending":
      return (
        <Button variant="secondary" onClick={() => onProcess(document)} disabled={disabled} aria-label={`Process ${document.original_name}`}>
          <Play size={14} aria-hidden="true" /> Process
        </Button>
      )
    case "flagged":
      return (
        <Button variant="secondary" onClick={() => onReview(document)} disabled={disabled} aria-label={`Review ${document.original_name}`}>
          <ShieldAlert size={14} aria-hidden="true" /> Review
        </Button>
      )
    case "processed":
      return (
        <Button variant="ghost" onClick={() => onProcess(document)} disabled={disabled} aria-label={`Process ${document.original_name} again`}>
          <RefreshCw size={14} aria-hidden="true" /> Process again
        </Button>
      )
    default:
      // failed, processing (possibly stuck after a crash) or a status we do not know: let the admin retry
      return (
        <Button variant="secondary" onClick={() => onProcess(document)} disabled={disabled} aria-label={`Retry ${document.original_name}`}>
          <RefreshCw size={14} aria-hidden="true" /> Retry
        </Button>
      )
  }
}

export function DocumentTable({ documents, busyIds, onProcess, onReview, onDelete }: DocumentTableProps) {
  if (documents.length === 0) {
    return <p className="my-8 text-center text-muted">No documents yet. Upload a PDF or TXT file above.</p>
  }

  return (
    <div className="overflow-x-auto rounded-card border border-line bg-surface shadow-card">
      <table className="w-full border-collapse text-[0.925rem] max-sm:block">
        <caption className="sr-only">Documents</caption>
        <thead className="max-sm:sr-only">
          <tr>
            <th scope="col" className={HEADER_CELL}>
              Name
            </th>
            <th scope="col" className={HEADER_CELL}>
              Status
            </th>
            <th scope="col" className={HEADER_CELL}>
              Uploaded
            </th>
            <th scope="col" className={HEADER_CELL}>
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody className="max-sm:block">
          {documents.map((document) => {
            const busy = busyIds.has(document.id)
            return (
              <tr key={document.id} className="last:*:border-b-0 max-sm:block max-sm:border-b max-sm:border-line max-sm:px-4 max-sm:py-3 max-sm:last:border-b-0">
                <td className={CELL}>
                  <div className="flex min-w-56 items-center gap-2 wrap-anywhere max-sm:min-w-0">
                    <FileText size={16} className="flex-none text-muted" aria-hidden="true" />
                    <span>{document.original_name}</span>
                    <span className="flex-none rounded-sm border border-line px-[0.4rem] text-[0.7rem] text-muted">
                      {document.file_type.toUpperCase()}
                    </span>
                  </div>
                </td>
                <td className={CELL}>
                  {busy ? <span className="text-[0.8rem] text-accent">Working...</span> : <StatusBadge status={document.status} />}
                </td>
                <td className={`${CELL} whitespace-nowrap text-muted`}>{formatTime(document.created_at)}</td>
                <td className={`${CELL} text-right whitespace-nowrap max-sm:mt-[0.4rem] max-sm:text-left *:not-first:ml-1`}>
                  {mainAction(document, onProcess, onReview, busy)}
                  <Button variant="ghost" onClick={() => onDelete(document)} disabled={busy} aria-label={`Delete ${document.original_name}`}>
                    <Trash2 size={14} aria-hidden="true" />
                  </Button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
