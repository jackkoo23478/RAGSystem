"use client"

import { useEffect, useState } from "react"

import { QueryStatusBadge } from "@/components/admin/QueryStatusBadge"
import { CitationList } from "@/components/chat/CitationList"
import { Button } from "@/components/ui/Button"
import { Modal } from "@/components/ui/Modal"
import { useEndSession } from "@/hooks/useEndSession"
import { isAuthError } from "@/lib/api/client"
import { getLog } from "@/lib/api/logs"
import { getToken } from "@/lib/auth/session"
import { formatLatency } from "@/lib/format/numbers"
import { formatTime } from "@/lib/format/time"
import type { QueryStatus } from "@/lib/types/rag"
import type { QueryLogDetail } from "@/lib/types/logs"

// What an admin is told when there is no answer to show. Not the wording a user sees: this one says what happened.
const NO_ANSWER_NOTE: Record<Exclude<QueryStatus, "answered">, string> = {
  no_evidence: "No passage was relevant enough, or the model said it had no answer, so nothing was answered.",
  invalid_answer: "The model's answer had no valid source reference, so it was not accepted and is not shown.",
  failed: "The language model was unavailable or failed while answering.",
}

type Loaded = { id: number; detail?: QueryLogDetail; error?: string }

interface LogDetailDialogProps {
  id: number | null // the dialog is open while an id is set
  onClose: () => void
}

export function LogDetailDialog({ id, onClose }: LogDetailDialogProps) {
  const endSession = useEndSession()
  const [loaded, setLoaded] = useState<Loaded | null>(null)

  useEffect(() => {
    if (id === null) return
    const token = getToken()
    if (!token) {
      endSession()
      return
    }

    let cancelled = false
    getLog(token, id)
      .then((detail) => {
        if (!cancelled) setLoaded({ id, detail })
      })
      .catch((err) => {
        if (cancelled) return
        if (isAuthError(err)) endSession()
        else setLoaded({ id, error: err instanceof Error ? err.message : "Something went wrong. Please try again later." })
      })
    return () => {
      cancelled = true
    }
  }, [id, endSession])

  // what was loaded for another question earlier is not shown while this one loads
  const current = loaded && loaded.id === id ? loaded : null
  const detail = current?.detail

  return (
    <Modal open={id !== null} onClose={onClose} labelledBy="log-detail-title" wide>
      <h2 id="log-detail-title" className="mb-3 text-[1.15rem] font-bold">
        Question details
      </h2>

      {current?.error && (
        <p role="alert" className="rounded-control bg-danger-soft px-4 py-3 text-danger">
          {current.error}
        </p>
      )}
      {!current && <p className="text-muted">Loading…</p>}

      {detail && (
        <div className="space-y-4">
          <div>
            <p className="text-xs font-semibold tracking-wider text-muted uppercase">Question</p>
            <p className="wrap-anywhere whitespace-pre-wrap">{detail.question}</p>
          </div>

          <dl className="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm text-muted">
            <div className="flex gap-1">
              <dt>Asked by</dt>
              <dd className="text-ink">{detail.user_email}</dd>
            </div>
            <div className="flex gap-1">
              <dt>Time</dt>
              <dd className="text-ink">{formatTime(detail.created_at)}</dd>
            </div>
            <div className="flex gap-1">
              <dt>Response time</dt>
              <dd className="text-ink">{formatLatency(detail.latency_ms)}</dd>
            </div>
            <div>
              <QueryStatusBadge status={detail.status} />
            </div>
          </dl>

          <div>
            <p className="text-xs font-semibold tracking-wider text-muted uppercase">Answer</p>
            {detail.status === "answered" && detail.answer ? (
              <p className="leading-[1.65] wrap-anywhere whitespace-pre-wrap">{detail.answer}</p>
            ) : (
              <p className="text-muted">{NO_ANSWER_NOTE[detail.status === "answered" ? "failed" : detail.status]}</p>
            )}
          </div>

          <CitationList citations={detail.citations} />
        </div>
      )}

      <div className="mt-5 flex justify-end">
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      </div>
    </Modal>
  )
}
