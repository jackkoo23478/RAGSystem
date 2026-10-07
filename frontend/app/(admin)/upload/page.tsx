"use client"

import { useCallback, useEffect, useState } from "react"
import { CircleCheck, TriangleAlert, X } from "lucide-react"

import { DocumentTable } from "@/components/admin/DocumentTable"
import { UploadForm } from "@/components/admin/UploadForm"
import { Button } from "@/components/ui/Button"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { useEndSession } from "@/hooks/useEndSession"
import { isAuthError } from "@/lib/api/client"
import { deleteDocument, flaggedSignals, ingestDocument, listDocuments, uploadDocument } from "@/lib/api/documents"
import { getToken } from "@/lib/auth/session"
import { cn } from "@/lib/cn"
import type { DocumentItem } from "@/lib/types/document"

type Notice = { tone: "success" | "warning" | "error"; text: string }

const NOTICE_TONES: Record<Notice["tone"], string> = {
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  error: "bg-danger-soft text-danger",
}

function errorText(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong. Please try again later."
}

// newest first
function byNewest(documents: DocumentItem[]): DocumentItem[] {
  return [...documents].sort((a, b) => b.id - a.id)
}

export default function DocumentsPage() {
  const endSession = useEndSession()
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [notice, setNotice] = useState<Notice | null>(null)
  const [uploading, setUploading] = useState(false)
  const [busyIds, setBusyIds] = useState<ReadonlySet<number>>(new Set())
  // why a document was held back; only known for flags seen in this session
  const [signals, setSignals] = useState<Record<number, string[]>>({})
  const [reviewing, setReviewing] = useState<DocumentItem | null>(null)
  const [deleting, setDeleting] = useState<DocumentItem | null>(null)

  const setBusy = (id: number, busy: boolean) =>
    setBusyIds((previous) => {
      const next = new Set(previous)
      if (busy) next.add(id)
      else next.delete(id)
      return next
    })

  const loadDocuments = useCallback(
    async (token: string) => {
      try {
        setDocuments(byNewest(await listDocuments(token)))
        setLoadError(null)
      } catch (err) {
        if (isAuthError(err)) endSession()
        else setLoadError(errorText(err))
      } finally {
        setLoading(false)
      }
    },
    [endSession],
  )

  useEffect(() => {
    const token = getToken()
    if (!token) {
      endSession()
      return
    }
    loadDocuments(token)
  }, [endSession, loadDocuments])

  // process one document (extract, scan, chunk, embed, store); the request returns when it is done
  const runIngest = async (token: string, document: DocumentItem, allowSuspicious = false) => {
    setBusy(document.id, true)
    try {
      const updated = await ingestDocument(token, document.id, allowSuspicious)
      setDocuments((previous) => previous.map((item) => (item.id === updated.id ? updated : item)))
      setSignals((previous) => {
        const { [document.id]: _removed, ...rest } = previous
        return rest
      })
      setNotice({ tone: "success", text: `${document.original_name} is ready. You can now ask questions about it.` })
    } catch (err) {
      if (isAuthError(err)) {
        endSession()
        return
      }
      const found = flaggedSignals(err)
      if (found) {
        setSignals((previous) => ({ ...previous, [document.id]: found }))
        setNotice({
          tone: "warning",
          text: `${document.original_name} was held for review: its text looks like instructions aimed at an AI model.`,
        })
      } else {
        setNotice({ tone: "error", text: `${document.original_name}: ${errorText(err)}` })
      }
      await loadDocuments(token) // the status changed on the server (flagged or failed)
    } finally {
      setBusy(document.id, false)
    }
  }

  const handleUpload = async (file: File, processNow: boolean): Promise<boolean> => {
    const token = getToken()
    if (!token) {
      endSession()
      return false
    }

    setUploading(true)
    setNotice(null)
    try {
      const uploaded = await uploadDocument(token, file)
      setDocuments((previous) => byNewest([uploaded, ...previous]))
      if (processNow) await runIngest(token, uploaded)
      else setNotice({ tone: "success", text: `${uploaded.original_name} was uploaded. Process it to make it searchable.` })
      return true
    } catch (err) {
      if (isAuthError(err)) {
        endSession()
        return false
      }
      setNotice({ tone: "error", text: errorText(err) })
      return false
    } finally {
      setUploading(false)
    }
  }

  const handleProcess = (document: DocumentItem) => {
    const token = getToken()
    if (!token) return endSession()
    setNotice(null)
    runIngest(token, document)
  }

  const confirmReview = () => {
    const document = reviewing
    const token = getToken()
    setReviewing(null)
    if (!document) return
    if (!token) return endSession()
    setNotice(null)
    runIngest(token, document, true)
  }

  const confirmDelete = async () => {
    const document = deleting
    const token = getToken()
    if (!document) return
    if (!token) return endSession()

    setBusy(document.id, true)
    try {
      await deleteDocument(token, document.id)
      setDocuments((previous) => previous.filter((item) => item.id !== document.id))
      setNotice({ tone: "success", text: `${document.original_name} was deleted.` })
    } catch (err) {
      if (isAuthError(err)) {
        endSession()
        return
      }
      setNotice({ tone: "error", text: `${document.original_name}: ${errorText(err)}` })
    } finally {
      setBusy(document.id, false)
      setDeleting(null)
    }
  }

  const NoticeIcon = notice?.tone === "success" ? CircleCheck : TriangleAlert

  return (
    <main>
      <h1 className="text-2xl font-semibold">Documents</h1>
      <p className="mt-1 mb-5 text-muted">
        Upload PDF or TXT files and process them. Only processed documents are used to answer questions.
      </p>

      <UploadForm onUpload={handleUpload} disabled={uploading} />

      {notice && (
        <div
          className={cn("mt-4 flex items-start gap-[0.6rem] rounded-control py-[0.6rem] pr-3 pl-4", NOTICE_TONES[notice.tone])}
          role={notice.tone === "error" ? "alert" : "status"}
        >
          <NoticeIcon size={18} className="mt-[0.2rem] flex-none" aria-hidden="true" />
          <span className="flex-1 wrap-anywhere">{notice.text}</span>
          <Button variant="ghost" className="min-h-7 px-[0.4rem] text-inherit" onClick={() => setNotice(null)} aria-label="Dismiss message">
            <X size={16} aria-hidden="true" />
          </Button>
        </div>
      )}

      <section className="mt-6" aria-busy={loading}>
        {loading && <p className="text-muted">Loading documents…</p>}
        {loadError && (
          <p role="alert" className="rounded-control bg-danger-soft px-4 py-3 text-danger">
            {loadError}
          </p>
        )}
        {!loading && !loadError && (
          <DocumentTable
            documents={documents}
            busyIds={busyIds}
            onProcess={handleProcess}
            onReview={setReviewing}
            onDelete={setDeleting}
          />
        )}
      </section>

      <ConfirmDialog
        open={reviewing !== null}
        title="Review a flagged document"
        confirmLabel="Process anyway"
        onConfirm={confirmReview}
        onCancel={() => setReviewing(null)}
      >
        <p>
          <strong>{reviewing?.original_name}</strong> was not made searchable because its text looks like instructions aimed
          at an AI model (for example &quot;ignore all previous instructions&quot;).
        </p>
        {reviewing && signals[reviewing.id] && (
          <p>
            Matched: <code>{signals[reviewing.id].join(", ")}</code>
          </p>
        )}
        <p>Read the original file first. Process it only if the text is safe; otherwise delete it.</p>
      </ConfirmDialog>

      <ConfirmDialog
        open={deleting !== null}
        title="Delete this document?"
        confirmLabel="Delete"
        tone="danger"
        busy={deleting !== null && busyIds.has(deleting.id)}
        onConfirm={confirmDelete}
        onCancel={() => setDeleting(null)}
      >
        <p>
          <strong>{deleting?.original_name}</strong> will be removed together with its stored file and its search entries. Past
          answers keep the sources they showed.
        </p>
      </ConfirmDialog>
    </main>
  )
}
