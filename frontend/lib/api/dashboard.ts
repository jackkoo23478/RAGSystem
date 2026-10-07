import { apiRequest } from "./client"
import type { DailyActivity, DashboardSummary } from "../types/dashboard"
import type { DocumentItem } from "../types/document"
import type { QueryLogItem } from "../types/logs"

function authHeaders(token: string) {
    return { Authorization: `Bearer ${token}` }
}

export function getSummary(token: string) {
    return apiRequest<DashboardSummary>("/api/v1/dashboard/summary", {
        headers: authHeaders(token),
    })
}

export function getActivity(token: string, days: number) {
    return apiRequest<DailyActivity[]>(`/api/v1/dashboard/activity?days=${days}`, {
        headers: authHeaders(token),
    })
}

export function getRecentDocuments(token: string, limit = 5) {
    return apiRequest<DocumentItem[]>(`/api/v1/dashboard/recent-documents?limit=${limit}`, {
        headers: authHeaders(token),
    })
}

export function getRecentQueries(token: string, limit = 5) {
    return apiRequest<QueryLogItem[]>(`/api/v1/dashboard/recent-queries?limit=${limit}`, {
        headers: authHeaders(token),
    })
}
