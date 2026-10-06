import { apiRequest } from "./client"
import type { QueryResult, QueryHistoryItem, QueryDetail } from "../types/rag"

function authHeaders(token: string) {
    return { Authorization: `Bearer ${token}` }
}

export function askQuestion(token: string, question: string) {
    return apiRequest<QueryResult>("/api/v1/rag/query", {
        method: "POST",
        headers: authHeaders(token),
        body: JSON.stringify({ question }),
    })
}

export function listQueries(token: string, limit = 20) {
    return apiRequest<QueryHistoryItem[]>(`/api/v1/rag/queries?limit=${limit}`, {
        headers: authHeaders(token),
    })
}

export function getQuery(token: string, id: number) {
    return apiRequest<QueryDetail>(`/api/v1/rag/queries/${id}`, {
        headers: authHeaders(token),
    })
}