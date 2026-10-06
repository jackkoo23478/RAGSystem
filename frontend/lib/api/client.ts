const BASEURL = process.env.NEXT_PUBLIC_API_URL;

export class ApiError extends Error {
    status: number

    constructor(message: string, status: number) {
        super(message)
        this.name = "ApiError"
        this.status = status
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
    try {
        response = await fetch(`${BASEURL}${path}`, {
            ...options,
            headers: {
                "Content-Type": "application/json",
                ...options.headers,
            },
        })
    } catch {
        // fetch only throws when no HTTP response arrived at all (server down, network error)
        throw new ApiError("Cannot connect to server , please try again", 0)
    }

    if (!response.ok) {
        const errorBody = await response.json().catch(() => null)
        throw new ApiError(detailToMessage(errorBody?.detail), response.status)
    }
    return response.json() as Promise<T>
}

// 401 (invalid or expired token) and 403 (no token on older FastAPI versions) both mean: log in again
export function isAuthError(err: unknown): boolean {
    return err instanceof ApiError && (err.status === 401 || err.status === 403)
}
