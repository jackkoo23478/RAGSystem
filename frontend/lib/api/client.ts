const BASEURL = process.env.NEXT_PUBLIC_API_URL;

export class ApiError extends Error {
    status: number
    detail: unknown // the raw `detail` from the backend, for callers that need more than the message

    constructor(message: string, status: number, detail: unknown = undefined) {
        super(message)
        this.name = "ApiError"
        this.status = status
        this.detail = detail
    }
}

const FALLBACK_MESSAGE = "Something went wrong. Please try again later."

// The backend sends `detail` in three shapes: a string, a list of field errors
// (validation), or an object with a `message`. Turn any of them into one readable line.
export function detailToMessage(detail: unknown): string {
    if (typeof detail === "string") return detail

    if (Array.isArray(detail)) {
        const messages = detail.map((item) =>
            item && typeof item === "object" && "msg" in item ? String(item.msg) : "wrong input"
        )
        return messages.length > 0 ? messages.join("; ") : FALLBACK_MESSAGE
    }

    if (detail && typeof detail === "object" && "message" in detail) {
        return String(detail.message)
    }

    return FALLBACK_MESSAGE
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
    let response: Response
    // a file upload must NOT get a Content-Type: the browser adds one with the multipart boundary
    const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData
    try {
        response = await fetch(`${BASEURL}${path}`, {
            ...options,
            headers: {
                ...(isFormData ? {} : { "Content-Type": "application/json" }),
                ...options.headers,
            },
        })
    } catch {
        // fetch only throws when no HTTP response arrived at all (server down, network error)
        throw new ApiError("Cannot connect to server , please try again", 0)
    }

    if (!response.ok) {
        const errorBody = await response.json().catch(() => null)
        throw new ApiError(detailToMessage(errorBody?.detail), response.status, errorBody?.detail)
    }
    if (response.status === 204) return undefined as T // "no content", e.g. after a delete: there is no body to parse
    return response.json() as Promise<T>
}

// 401 (invalid or expired token) and 403 (no token on older FastAPI versions) both mean: log in again
export function isAuthError(err: unknown): boolean {
    return err instanceof ApiError && (err.status === 401 || err.status === 403)
}
