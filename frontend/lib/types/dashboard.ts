export interface DocumentCounts {
    total: number
    pending: number
    processing: number
    processed: number
    failed: number
    flagged: number
}

export interface QueryCounts {
    total: number
    answered: number
    no_evidence: number
    invalid_answer: number
    failed: number
}

export interface DashboardSummary {
    documents: DocumentCounts
    queries: QueryCounts
    answer_rate: number | null // null while nothing was asked yet
    avg_latency_ms: number | null // null while no query has a recorded latency
}

// one UTC day; a day without questions is sent as zero (and no average), never left out
export interface DailyActivity {
    date: string // "2026-10-07"
    queries: number
    answered: number
    avg_latency_ms: number | null
}
