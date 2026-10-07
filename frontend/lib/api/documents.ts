import { apiRequest, ApiError } from "./client"
import type { DocumentItem } from "../types/document"

function authHeaders(token: string) {
    return { Authorization: `Bearer ${token}` }
}

export function listDocuments(token: string) {
    return apiRequest<DocumentItem[]>("/api/v1/documents", {
        headers: authHeaders(token),
    })
}

export function uploadDocument(token: string, file: File) {
    const form = new FormData()
    form.append("file", file) // the backend reads the upload from the field called "file"
    return apiRequest<DocumentItem>("/api/v1/documents/upload", {
        method: "POST",
        headers: authHeaders(token),
        body: form,
    })
}

// allowSuspicious: an admin has read a flagged document and decided it is safe
export function ingestDocument(token: string, id: number, allowSuspicious = false) {
    const query = allowSuspicious ? "?allow_suspicious=true" : ""
    return apiRequest<DocumentItem>(`/api/v1/documents/${id}/ingest${query}`, {
        method: "POST",
        headers: authHeaders(token),
    })
}

export function deleteDocument(token: string, id: number) {
    return apiRequest<void>(`/api/v1/documents/${id}`, {
        method: "DELETE",
        headers: authHeaders(token),
    })
}

// When ingest holds a document back, the backend answers 422 with { message, signals: [...] }.
// Returns the signals, or null when the error is something else.
export function flaggedSignals(err: unknown): string[] | null {
    if (!(err instanceof ApiError) || err.status !== 422) return null
    const detail = err.detail
    if (detail && typeof detail === "object" && "signals" in detail && Array.isArray(detail.signals)) {
        return detail.signals.map(String)
    }
    return null
}
