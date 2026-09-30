const COOKIE_NAME = "user_token";

export function saveToken(token: string) {
    document.cookie = `${COOKIE_NAME}=${token}; path=/; max-age=3600; secure; samesite=strict`;
}

export function getToken(): string | null {
    const match = document.cookie
        .split("; ")
        .find((row) => row.startsWith(`${COOKIE_NAME}=`));
    return match ? match.split("=")[1] : null;
}

export function clearToken() {
    document.cookie = `${COOKIE_NAME}=; path=/; max-age=0; secure; samesite=strict`;
}