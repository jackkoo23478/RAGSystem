'use client'

import { useEffect, useState } from "react"
import { getToken } from "@/lib/auth/session"
import type { User } from "@/lib/types/auth"
import { getMe } from "@/lib/api/auth"

export default function ChatPage() {
  const [user, setUser] = useState<User | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      setError("No token found. Please log in.")
      return
    }

    getMe(token)
      .then(setUser)
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to fetch user data.")
      })
  }, [])

  if (error) return <main style={{ padding: '2rem' }}>{error}</main>
  if (!user) return <main style={{ padding: '2rem' }}>Loading user data...</main>

  return (
    <main style={{ padding: '2rem' }}>
      <p>歡迎返嚟,{user.email}</p>
      <p>身份:{user.role}</p>
    </main>
  )
}