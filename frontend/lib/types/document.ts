// The backend stores the status as free text, but these are the values it actually uses:
// pending -> processing -> processed, or failed, or flagged (held for an admin to review).
export type DocumentStatus = "pending" | "processing" | "processed" | "failed" | "flagged"

export interface DocumentItem {
    id: number
    original_name: string
    file_type: string
    status: DocumentStatus
    created_at: string
    uploaded_by: number
}
