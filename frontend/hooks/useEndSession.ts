"use client"

import { useCallback } from "react"
import { useRouter } from "next/navigation"

import { clearToken } from "@/lib/auth/session"

// The token is missing, expired or rejected, or the user logs out: forget it and go to the login page.
export function useEndSession() {
  const router = useRouter()
  return useCallback(() => {
    clearToken()
    router.replace("/login")
  }, [router])
}
