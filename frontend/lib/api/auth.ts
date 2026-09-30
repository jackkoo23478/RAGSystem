import { apiRequest } from "./client";
import type { LoginCredentials, RegisterCredentials, User, AuthTokens } from "../types/auth";

export function register(data: RegisterCredentials) {
    return apiRequest<User>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify(data),
    });
}

export function login(data: LoginCredentials) {
    return apiRequest<AuthTokens>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify(data),
    });
}

export function getMe(token: string) {
    return apiRequest<User>("/api/v1/auth/me", {
        headers: {
            Authorization: `Bearer ${token}`,
        },
    });
}