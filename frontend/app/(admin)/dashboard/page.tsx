"use client"

import Link from "next/link"
import { useEffect, useState } from "react"

import { ChartCard } from "@/components/admin/ChartCard"
import { QueryStatusBadge } from "@/components/admin/QueryStatusBadge"
import { RangeFilter } from "@/components/admin/RangeFilter"
import { StatCard } from "@/components/admin/StatCard"
import { StatusBadge } from "@/components/admin/StatusBadge"
import { TrendChart } from "@/components/admin/TrendChart"
import { useEndSession } from "@/hooks/useEndSession"
import { isAuthError } from "@/lib/api/client"
import { getActivity, getRecentDocuments, getRecentQueries, getSummary } from "@/lib/api/dashboard"
import { getToken } from "@/lib/auth/session"
import { formatDay, formatLatency, formatPercent } from "@/lib/format/numbers"
import { formatTime } from "@/lib/format/time"
import type { DailyActivity, DashboardSummary } from "@/lib/types/dashboard"
import type { DocumentItem } from "@/lib/types/document"
import type { QueryLogItem } from "@/lib/types/logs"

const RANGES = [7, 14, 30] as const
const DEFAULT_DAYS = 14

function errorText(err: unknown): string {
  return err instanceof Error ? err.message : "Something went wrong. Please try again later."
}

const TABLE = "w-full text-left tabular-nums" // tabular figures: the numbers sit in columns
const TH = "px-2 py-1 font-medium text-muted"
const TD = "border-t border-line px-2 py-1"

export default function DashboardPage() {
  const endSession = useEndSession()
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [recentQueries, setRecentQueries] = useState<QueryLogItem[]>([])
  const [recentDocuments, setRecentDocuments] = useState<DocumentItem[]>([])
  const [days, setDays] = useState<number>(DEFAULT_DAYS)
  const [activity, setActivity] = useState<DailyActivity[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  // the numbers and the two recent lists: loaded once when the page opens
  useEffect(() => {
    const token = getToken()
    if (!token) {
      endSession()
      return
    }

    let cancelled = false
    Promise.all([getSummary(token), getRecentQueries(token), getRecentDocuments(token)])
      .then(([nextSummary, queries, documents]) => {
        if (cancelled) return
        setSummary(nextSummary)
        setRecentQueries(queries)
        setRecentDocuments(documents)
      })
      .catch((err) => {
        if (cancelled) return
        if (isAuthError(err)) endSession()
        else setError(errorText(err))
      })
    return () => {
      cancelled = true
    }
  }, [endSession])

  // the daily activity: loaded again whenever the time range changes
  useEffect(() => {
    const token = getToken()
    if (!token) return

    let cancelled = false
    getActivity(token, days)
      .then((rows) => {
        if (!cancelled) setActivity(rows)
      })
      .catch((err) => {
        if (cancelled) return
        if (isAuthError(err)) endSession()
        else setError(errorText(err))
      })
    return () => {
      cancelled = true
    }
  }, [days, endSession])

  // the chart shows the previous range, faded, until the new one arrives
  const refreshing = activity !== null && activity.length !== days
  const hasLatency = activity?.some((row) => row.avg_latency_ms !== null) ?? false
  const docs = summary?.documents
  const queries = summary?.queries

  return (
    <main>
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <p className="mt-1 mb-5 text-muted">How the system is used: documents, questions and how long answers take.</p>

      {error && (
        <p role="alert" className="mb-5 rounded-control bg-danger-soft px-4 py-3 text-danger">
          {error}
        </p>
      )}

      <dl className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          label="Documents"
          value={docs ? String(docs.total) : "–"}
          note={docs ? `${docs.processed} ready${docs.total > docs.processed ? `, ${docs.total - docs.processed} not ready` : ""}` : undefined}
        />
        <StatCard label="Questions" value={queries ? String(queries.total) : "–"} note="All time" />
        <StatCard
          label="Answer rate"
          value={formatPercent(summary?.answer_rate ?? null)}
          note={queries ? (queries.total > 0 ? `${queries.answered} of ${queries.total} got an answer` : "No questions yet") : undefined}
        />
        <StatCard label="Average response time" value={formatLatency(summary?.avg_latency_ms ?? null)} note="Questions with a recorded time" />
      </dl>

      <div className="mt-8 mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Activity</h2>
        <RangeFilter options={RANGES} value={days} onChange={setDays} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard
          title="Questions per day"
          description="All questions and the ones that got an answer, per UTC day."
          refreshing={refreshing}
          table={
            <table className={TABLE}>
              <thead>
                <tr>
                  <th className={TH}>Day</th>
                  <th className={TH}>Questions</th>
                  <th className={TH}>Answered</th>
                </tr>
              </thead>
              <tbody>
                {[...(activity ?? [])].reverse().map((row) => (
                  <tr key={row.date}>
                    <td className={TD}>{formatDay(row.date)}</td>
                    <td className={TD}>{row.queries}</td>
                    <td className={TD}>{row.answered}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          }
        >
          {activity && (
            <TrendChart
              rows={activity}
              series={[
                { key: "queries", label: "Questions", color: "var(--series-1)" },
                { key: "answered", label: "Answered", color: "var(--series-2)" },
              ]}
              formatValue={(value) => String(value)}
              integersOnly
              ariaLabel={`Questions per day over the last ${days} days`}
            />
          )}
        </ChartCard>

        <ChartCard
          title="Average response time"
          description="From receiving a question to saving the answer, per UTC day."
          refreshing={refreshing}
          table={
            <table className={TABLE}>
              <thead>
                <tr>
                  <th className={TH}>Day</th>
                  <th className={TH}>Average</th>
                </tr>
              </thead>
              <tbody>
                {[...(activity ?? [])].reverse().map((row) => (
                  <tr key={row.date}>
                    <td className={TD}>{formatDay(row.date)}</td>
                    <td className={TD}>{formatLatency(row.avg_latency_ms)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          }
        >
          {activity &&
            (hasLatency ? (
              <TrendChart
                rows={activity}
                series={[{ key: "avg_latency_ms", label: "Average response time", color: "var(--series-1)" }]}
                formatValue={formatLatency}
                ariaLabel={`Average response time per day over the last ${days} days`}
              />
            ) : (
              <p className="py-16 text-center text-muted">No response times were recorded in this period.</p>
            ))}
        </ChartCard>
      </div>

      <div className="mt-8 grid gap-4 lg:grid-cols-2">
        <section className="min-w-0 rounded-card border border-line bg-surface p-5 shadow-card" aria-labelledby="recent-questions">
          <div className="flex items-baseline justify-between gap-3">
            <h2 id="recent-questions" className="text-base font-semibold">
              Recent questions
            </h2>
            <Link href="/logs" className="text-sm text-accent hover:underline">
              View all
            </Link>
          </div>
          {recentQueries.length === 0 ? (
            <p className="mt-3 text-muted">No questions yet.</p>
          ) : (
            <ul className="mt-3 divide-y divide-line">
              {recentQueries.map((item) => (
                <li key={item.id} className="flex items-start justify-between gap-3 py-2">
                  <div className="min-w-0">
                    <p className="truncate">{item.question}</p>
                    <p className="truncate text-sm text-muted">
                      {item.user_email} · {formatTime(item.created_at)}
                    </p>
                  </div>
                  <QueryStatusBadge status={item.status} />
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="min-w-0 rounded-card border border-line bg-surface p-5 shadow-card" aria-labelledby="recent-documents">
          <div className="flex items-baseline justify-between gap-3">
            <h2 id="recent-documents" className="text-base font-semibold">
              Recent documents
            </h2>
            <Link href="/upload" className="text-sm text-accent hover:underline">
              Manage
            </Link>
          </div>
          {recentDocuments.length === 0 ? (
            <p className="mt-3 text-muted">No documents yet.</p>
          ) : (
            <ul className="mt-3 divide-y divide-line">
              {recentDocuments.map((item) => (
                <li key={item.id} className="flex items-start justify-between gap-3 py-2">
                  <div className="min-w-0">
                    <p className="truncate">{item.original_name}</p>
                    <p className="text-sm text-muted">{formatTime(item.created_at)}</p>
                  </div>
                  <StatusBadge status={item.status} />
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  )
}
