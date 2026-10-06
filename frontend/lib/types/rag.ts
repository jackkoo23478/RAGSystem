export type QueryStatus = "answered" | "no_evidence" | "invalid_answer" | "failed"

export interface Citation {
    number: number | null
    document_id: number | null
    document_name: string
    page_number: number | null
    snippet: string
    score: number
}

export interface QueryResult {
    query_id: number
    status: QueryStatus
    answer: string | null
    citations: Citation[]
}

export interface QueryHistoryItem {
    id: number
    question: string
    status: QueryStatus
    answer: string | null
    created_at: string
}

export interface QueryDetail extends QueryHistoryItem {
    citations: Citation[]
}