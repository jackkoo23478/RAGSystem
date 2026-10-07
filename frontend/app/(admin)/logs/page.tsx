"use client"

import { useEffect, useState } from "react"
import { ChevronLeft, ChevronRight, Search } from "lucide-react"

import { LogDetailDialog } from "@/components/admin/LogDetailDialog"
import { LogTable } from "@/components/admin/LogTable"
import { Button } from "@/components/ui/Button"
import { useEndSession } from "@/hooks/useEndSession"
import { isAuthError } from "@/lib/api/client"
import { listLogs } from "@/lib/api/logs"
import { getToken } from "@/lib/auth/session"
import { cn } from "@/lib/cn"
import type { QueryLogPage } from "@/lib/types/logs"
import type { QueryStatus } from "@/lib/types/rag"

const PAGE_SIZE = 20
const SEARCH_DELAY_MS = 300

const STATUS_OPTIONS: { value: QueryStatus | ""; label: string }[] = [
  { value: "", label: "All statuses" },
  { value: "answered", label: "Answered" },
  { value: "no_evidence", label: "No sources" },
  { value: "invalid_answer", label: "Unreliable" },
  { value: "failed", label: "Error" },
]

const CONTROL =
  "min-h-10 rounded-control border border-line bg-surface px-3 text-ink placeholder:text-muted"

function errorText(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong. Please try again later."
}

export default function LogsPage() {
  const endSession = useEndSession()
  const [status, setStatus] = useState<QueryStatus | "">("")
  const [searchInput, setSearchInput] = useState("") // what is typed
  const [search, setSearch] = useState("") // what is sent: the typed text, after a short pause
  const [offset, setOffset] = useState(0)
  const [page, setPage] = useState<QueryLogPage | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [openId, setOpenId] = useState<number | null>(null)

  // search while typing, but not on every key: wait until the typing pauses
  useEffect(() => {
    const trimmed = searchInput.trim()
    if (trimmed === search) return
    const timer = setTimeout(() => {
      setSearch(trimmed)
      setOffset(0)
    }, SEARCH_DELAY_MS)
    return () => clearTimeout(timer)
  }, [searchInput, search])

  useEffect(() => {
    const token = getToken()
    if (!token) {
      endSession()
      return
    }

    let cancelled = false
    setLoading(true)
    listLogs(token, { status: status || null, search }, PAGE_SIZE, offset)
      .then((result) => {
        if (cancelled) return
        setPage(result)
        setError(null)
      })
      .catch((err) => {
        if (cancelled) return
        if (isAuthError(err)) endSession()
        else setError(errorText(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [status, search, offset, endSession])

  const total = page?.total ?? 0
  const from = total === 0 ? 0 : offset + 1
  const to = Math.min(offset + PAGE_SIZE, total)
  const filtered = status !== "" || search !== ""

  return (
    <main>
      <h1 className="text-2xl font-semibold">Question log</h1>
      <p className="mt-1 mb-5 text-muted">Every question asked by every user. Open one to see the answer and its sources.</p>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="relative">
          <span className="sr-only">Search questions or emails</span>
          <Search size={16} aria-hidden="true" className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-muted" />
          <input
            type="search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            maxLength={100}
            placeholder="Search questions or emails"
            className={cn(CONTROL, "w-72 max-w-full pl-9")}
          />
        </label>
        <label>
          <span className="sr-only">Status</span>
          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value as QueryStatus | "")
              setOffset(0)
            }}
            className={cn(CONTROL, "cursor-pointer")}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && (
        <p role="alert" className="rounded-control bg-danger-soft px-4 py-3 text-danger">
          {error}
        </p>
      )}

      {/* while a new page loads, the old rows stay, a little faded, so the page does not jump */}
      <div className={cn("transition-opacity duration-150", loading && page && "opacity-50")} aria-busy={loading}>
        {page === null && !error && <p className="text-muted">Loading…</p>}
        {page && page.items.length === 0 && (
          <p className="my-8 text-center text-muted">
            {filtered ? "No questions match these filters." : "No questions have been asked yet."}
          </p>
        )}
        {page && page.items.length > 0 && <LogTable items={page.items} onOpen={(item) => setOpenId(item.id)} />}
      </div>

      {page && page.total > 0 && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-muted tabular-nums">
            Showing {from}–{to} of {total}
          </p>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} disabled={offset === 0 || loading}>
              <ChevronLeft size={16} aria-hidden="true" /> Previous
            </Button>
            <Button variant="secondary" onClick={() => setOffset(offset + PAGE_SIZE)} disabled={to >= total || loading}>
              Next <ChevronRight size={16} aria-hidden="true" />
            </Button>
          </div>
        </div>
      )}

      <LogDetailDialog id={openId} onClose={() => setOpenId(null)} />
    </main>
  )
}
