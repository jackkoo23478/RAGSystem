'use client'

import { useCallback, useEffect, useRef, useState } from "react"
import Link from "next/link"
import { LogOut, Menu, Plus, ShieldCheck, TriangleAlert } from "lucide-react"

import { AnswerBubble } from "@/components/chat/AnswerBubble"
import { Composer } from "@/components/chat/Composer"
import { EmptyState } from "@/components/chat/EmptyState"
import { HistoryList } from "@/components/chat/HistoryList"
import { ThinkingIndicator } from "@/components/chat/ThinkingIndicator"
import { Button } from "@/components/ui/Button"
import { headerLink } from "@/components/ui/header-link"
import { useEndSession } from "@/hooks/useEndSession"
import { getMe } from "@/lib/api/auth"
import { ApiError, isAuthError } from "@/lib/api/client"
import { askQuestion, getQuery, listQueries } from "@/lib/api/rag"
import { getToken } from "@/lib/auth/session"
import { cn } from "@/lib/cn"
import type { User } from "@/lib/types/auth"
import type { QueryDetail, QueryHistoryItem, QueryResult } from "@/lib/types/rag"

// what the screen shows, not what the API returns: `kind` tells the three apart
type ChatMessage =
  | { id: string; kind: "user"; text: string }
  | { id: string; kind: "assistant"; result: QueryResult }
  | { id: string; kind: "error"; text: string }

// the backend answers 502 when the language model is down; say it in plain words
function errorText(err: unknown): string {
  if (err instanceof ApiError && err.status === 502) return "The AI model is temporarily unavailable. Please try again later."
  if (err instanceof Error) return err.message
  return "Something went wrong. Please try again later."
}

// a saved question has the same fields as a fresh answer, so the same bubble can show it
function toResult(detail: QueryDetail): QueryResult {
  return {
    query_id: detail.id,
    status: detail.status,
    answer: detail.answer,
    citations: detail.citations,
  }
}

export default function ChatPage() {
  const endSession = useEndSession()
  const [user, setUser] = useState<User | null>(null)
  const [history, setHistory] = useState<QueryHistoryItem[]>([])
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isWaiting, setIsWaiting] = useState(false)
  const [isLoadingItem, setIsLoadingItem] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false) // the history is a drawer on narrow screens
  const bottomRef = useRef<HTMLDivElement>(null)

  const busy = isWaiting || isLoadingItem

  const refreshHistory = useCallback(
    async (token: string) => {
      try {
        setHistory(await listQueries(token))
        setHistoryError(null)
      } catch (err) {
        if (isAuthError(err)) endSession()
        else setHistoryError(errorText(err))
      }
    },
    [endSession],
  )

  // who is logged in, and the saved questions; this also checks the token as soon as the page opens
  useEffect(() => {
    const token = getToken()
    if (!token) {
      endSession()
      return
    }

    let cancelled = false
    getMe(token)
      .then((me) => {
        if (!cancelled) setUser(me)
      })
      .catch((err) => {
        if (isAuthError(err)) endSession()
      })
    refreshHistory(token)

    return () => {
      cancelled = true
    }
  }, [endSession, refreshHistory])

  // keep the newest message in view
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isWaiting, isLoadingItem])

  const sendQuestion = async (question: string) => {
    const token = getToken()
    if (!token) {
      endSession()
      return
    }

    // use the (prev) form: two updates in a row must not overwrite each other
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), kind: "user", text: question }])
    setIsWaiting(true)

    try {
      const result = await askQuestion(token, question)
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), kind: "assistant", result }])
      setSelectedId(result.query_id)
      refreshHistory(token)
    } catch (err) {
      if (isAuthError(err)) {
        endSession()
        return
      }
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), kind: "error", text: errorText(err) }])
    } finally {
      setIsWaiting(false) // runs after success and after failure
    }
  }

  const openHistoryItem = async (id: number) => {
    const token = getToken()
    if (!token) {
      endSession()
      return
    }

    setHistoryOpen(false)
    setIsLoadingItem(true)
    try {
      const detail = await getQuery(token, id)
      setSelectedId(id)
      setMessages([
        { id: crypto.randomUUID(), kind: "user", text: detail.question },
        { id: crypto.randomUUID(), kind: "assistant", result: toResult(detail) },
      ])
    } catch (err) {
      if (isAuthError(err)) {
        endSession()
        return
      }
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), kind: "error", text: errorText(err) }])
    } finally {
      setIsLoadingItem(false)
    }
  }

  const startNewChat = () => {
    setMessages([])
    setSelectedId(null)
    setHistoryOpen(false)
  }

  return (
    <div className="grid h-dvh grid-cols-[18rem_minmax(0,1fr)] max-md:grid-cols-[minmax(0,1fr)]">
      {historyOpen && (
        <div className="hidden max-md:fixed max-md:inset-0 max-md:z-20 max-md:block max-md:bg-black/45" onClick={() => setHistoryOpen(false)} aria-hidden="true" />
      )}

      {/* on a narrow screen the history is a drawer that slides in from the left */}
      <aside
        className={cn(
          "flex flex-col gap-3 overflow-y-auto border-r border-line bg-surface p-4",
          "max-md:fixed max-md:inset-y-0 max-md:left-0 max-md:z-30 max-md:w-[min(18rem,85vw)]",
          historyOpen
            ? "max-md:visible max-md:translate-x-0 max-md:shadow-card max-md:transition-transform max-md:duration-200 max-md:ease-[ease]"
            : // a closed drawer must not take keyboard focus, so it turns invisible once it has slid out
              "max-md:invisible max-md:-translate-x-full max-md:[transition:transform_0.2s_ease,visibility_0s_linear_0.2s]",
        )}
        aria-label="Question history"
      >
        <Button variant="primary" fullWidth onClick={startNewChat} disabled={busy}>
          <Plus size={16} aria-hidden="true" />
          New chat
        </Button>
        <h2 className="mt-2 text-xs font-semibold tracking-wider text-muted uppercase">History</h2>
        <HistoryList
          items={history}
          selectedId={selectedId}
          disabled={busy}
          error={historyError}
          onSelect={openHistoryItem}
        />
      </aside>

      <main className="flex min-h-0 min-w-0 flex-col">
        <header className="flex items-center gap-2 border-b border-line bg-surface px-5 py-[0.6rem] max-md:px-3 max-md:py-2">
          <Button
            variant="ghost"
            className="hidden px-[0.6rem] max-md:inline-flex"
            aria-label="Open question history"
            onClick={() => setHistoryOpen(true)}
          >
            <Menu size={18} aria-hidden="true" />
          </Button>
          <h1 className="flex-1 text-[1.05rem] font-semibold">Document Q&A</h1>
          <div className="flex min-w-0 items-center gap-2 text-sm text-muted">
            {user?.role === "admin" && (
              <Link href="/upload" className={headerLink()}>
                <ShieldCheck size={16} aria-hidden="true" />
                <span className="max-md:hidden">Admin</span>
              </Link>
            )}
            {user && <span className="max-w-64 truncate max-md:hidden">{user.email}</span>}
            <Button variant="ghost" onClick={endSession} aria-label="Log out">
              <LogOut size={16} aria-hidden="true" />
              <span className="max-md:hidden">Log out</span>
            </Button>
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-6 max-md:px-3 max-md:py-4" aria-live="polite">
          <div className="mx-auto max-w-[46rem]">
            {messages.length === 0 && !busy && <EmptyState onPick={sendQuestion} disabled={busy} />}

            {messages.map((message) => {
              if (message.kind === "user") {
                return (
                  <div key={message.id} className="mt-5 flex justify-end">
                    <p className="max-w-[85%] rounded-card rounded-br-[4px] bg-accent px-4 py-[0.6rem] wrap-anywhere whitespace-pre-wrap text-accent-fg">
                      {message.text}
                    </p>
                  </div>
                )
              }
              if (message.kind === "assistant") {
                return <AnswerBubble key={message.id} result={message.result} />
              }
              return (
                <p key={message.id} role="alert" className="my-5 flex items-start gap-[0.6rem] rounded-control bg-danger-soft px-4 py-3 text-danger">
                  <TriangleAlert size={18} className="mt-[0.2rem] flex-none" aria-hidden="true" />
                  {message.text}
                </p>
              )
            })}

            {isWaiting && <ThinkingIndicator label="Thinking" />}
            {isLoadingItem && <ThinkingIndicator label="Loading" />}
            <div ref={bottomRef} />
          </div>
        </div>

        <Composer onSend={sendQuestion} disabled={busy} />
      </main>
    </div>
  )
}
