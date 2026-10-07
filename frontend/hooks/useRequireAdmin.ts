"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"

import { getMe } from "@/lib/api/auth"
import { isAuthError } from "@/lib/api/client"
import { getToken } from "@/lib/auth/session"
import type { User } from "@/lib/types/auth"

import { useEndSession } from "./useEndSession"

// Guards the admin pages. proxy.ts only checks that a cookie exists, so who the user really is
// (and whether they are an admin) has to be asked of the backend. The backend still enforces
// the role on every admin API call; this only keeps ordinary users from seeing admin screens.
export function useRequireAdmin() {
  const router = useRouter()
  const endSession = useEndSession()
  const [user, setUser] = useState<User | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const token = getToken()
    if (!token) {
      endSession()
      return
    }

    let cancelled = false
    getMe(token)
      .then((me) => {
        if (cancelled) return
        if (me.role !== "admin") {
          router.replace("/chat")
          return
        }
        setUser(me)
      })
      .catch((err) => {
        if (cancelled) return
        if (isAuthError(err)) endSession()
        else setError(err instanceof Error ? err.message : "Something went wrong. Please try again later.")
      })

    return () => {
      cancelled = true
    }
  }, [endSession, router])

  return { user, error }
}
