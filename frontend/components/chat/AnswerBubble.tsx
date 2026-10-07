import { Info, SearchX, TriangleAlert } from "lucide-react"
import type { LucideIcon } from "lucide-react"

import type { QueryResult, QueryStatus } from "@/lib/types/rag"

import { AssistantRow } from "./AssistantRow"
import { CitationList } from "./CitationList"

type NoAnswerStatus = Exclude<QueryStatus, "answered">

// What to tell the user when there is no answer to show. Every status needs an entry:
// if a new status is added to QueryStatus, TypeScript reports the missing case here.
export function noAnswerMessage(status: NoAnswerStatus): string {
  switch (status) {
    case "no_evidence":
      return "I could not find anything relevant in the documents. Try asking again with words that would appear in them."
    case "invalid_answer":
      return "The system could not produce a reliable answer with sources. Please try rephrasing your question."
    case "failed":
      return "Something went wrong while processing your question. Please try again later."
  }
}

const NOTICE_ICON: Record<NoAnswerStatus, LucideIcon> = {
  no_evidence: SearchX,
  invalid_answer: Info,
  failed: TriangleAlert,
}

export function AnswerBubble({ result }: { result: QueryResult }) {
  // an "answered" result always has text; the extra check keeps a broken response from showing an empty bubble
  if (result.status === "answered" && result.answer) {
    return (
      <AssistantRow>
        {/* pre-wrap keeps the line breaks of the answer */}
        <p className="leading-[1.65] wrap-anywhere whitespace-pre-wrap">{result.answer}</p>
        <CitationList citations={result.citations} />
      </AssistantRow>
    )
  }

  const status: NoAnswerStatus = result.status === "answered" ? "failed" : result.status
  const Icon = NOTICE_ICON[status]
  return (
    <AssistantRow quiet>
      <p className="flex items-start gap-[0.6rem] text-muted" role="status">
        <Icon size={18} className="mt-[0.2rem] flex-none" aria-hidden="true" />
        {noAnswerMessage(status)}
      </p>
    </AssistantRow>
  )
}
