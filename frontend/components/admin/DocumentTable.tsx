import { FileText, Play, RefreshCw, ShieldAlert, Trash2 } from "lucide-react"
import type { ReactNode } from "react"

import { Button } from "@/components/ui/Button"
import { formatTime } from "@/lib/format/time"
import type { DocumentItem } from "@/lib/types/document"

import { StatusBadge } from "./StatusBadge"
import styles from "./document-table.module.css"

interface DocumentTableProps {
  documents: DocumentItem[]
  busyIds: ReadonlySet<number>
  onProcess: (document: DocumentItem) => void
  onReview: (document: DocumentItem) => void
  onDelete: (document: DocumentItem) => void
}

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
    return <p className={styles.empty}>No documents yet. Upload a PDF or TXT file above.</p>
  }

  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <caption className={styles.caption}>Documents</caption>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Status</th>
            <th scope="col">Uploaded</th>
            <th scope="col">
              <span className={styles.srOnly}>Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {documents.map((document) => {
            const busy = busyIds.has(document.id)
            return (
              <tr key={document.id}>
                <td>
                  <div className={styles.name}>
                    <FileText size={16} className={styles.icon} aria-hidden="true" />
                    <span>{document.original_name}</span>
                    <span className={styles.type}>{document.file_type.toUpperCase()}</span>
                  </div>
                </td>
                <td>{busy ? <span className={styles.working}>Working...</span> : <StatusBadge status={document.status} />}</td>
                <td className={styles.time}>{formatTime(document.created_at)}</td>
                <td className={styles.actions}>
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
