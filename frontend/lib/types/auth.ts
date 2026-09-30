export interface LoginCredentials {
    email: string;
    password: string;
}

export interface RegisterCredentials {
    email: string;
    password: string;
}
export interface User {
    id: number,
    email: string,
    role: string
}

export interface AuthTokens {
    access_token: string,
    token_type: string
}