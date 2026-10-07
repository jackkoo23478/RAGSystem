import { apiRequest } from "./client"
import type { LogFilters, QueryLogDetail, QueryLogPage } from "../types/logs"

function authHeaders(token: string) {
    return { Authorization: `Bearer ${token}` }
}

export function listLogs(token: string, filters: LogFilters, limit: number, offset: number) {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
    if (filters.status) params.set("status", filters.status)
    if (filters.search.trim()) params.set("search", filters.search.trim())

    return apiRequest<QueryLogPage>(`/api/v1/logs?${params}`, {
        headers: authHeaders(token),
    })
}

export function getLog(token: string, id: number) {
    return apiRequest<QueryLogDetail>(`/api/v1/logs/${id}`, {
        headers: authHeaders(token),
    })
}
