import type { Citation, QueryStatus } from "./rag"

export interface QueryLogItem {
    id: number
    user_id: number
    user_email: string
    question: string
    status: QueryStatus
    latency_ms: number | null // null for questions from before latency was recorded
    created_at: string
}

export interface QueryLogPage {
    items: QueryLogItem[]
    total: number // all matches, not only this page
    limit: number
    offset: number
}

export interface QueryLogDetail extends QueryLogItem {
    answer: string | null // only a verified answer is ever sent
    citations: Citation[]
}

export interface LogFilters {
    status: QueryStatus | null
    search: string
}
