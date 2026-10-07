"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import type { ReactNode } from "react"
import { LogOut, MessageSquare } from "lucide-react"

import { Button } from "@/components/ui/Button"
import { headerLink } from "@/components/ui/header-link"
import { useEndSession } from "@/hooks/useEndSession"
import { useRequireAdmin } from "@/hooks/useRequireAdmin"

// the dashboard and logs pages are added to this list when they exist
const NAV = [{ href: "/upload", label: "Documents" }]

export default function AdminLayout({ children }: { children: ReactNode }) {
  const { user, error } = useRequireAdmin()
  const endSession = useEndSession()
  const pathname = usePathname()

  if (error) {
    return (
      <main className="grid min-h-dvh place-items-center text-muted">
        <p role="alert" className="rounded-control bg-danger-soft px-4 py-3 text-danger">
          {error}
        </p>
      </main>
    )
  }

  // nothing from the admin pages is shown until the backend has confirmed the user is an admin
  if (!user) {
    return (
      <main className="grid min-h-dvh place-items-center text-muted">
        <p role="status">Checking permissions…</p>
      </main>
    )
  }

  return (
    <div className="min-h-dvh">
      <header className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-line bg-surface px-5 py-[0.6rem]">
        <span className="font-semibold">Admin</span>
        <nav className="flex flex-1 gap-1" aria-label="Admin">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={headerLink(pathname.startsWith(item.href))}
              aria-current={pathname.startsWith(item.href) ? "page" : undefined}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="flex items-center gap-2 text-sm text-muted">
          <Link href="/chat" className={headerLink()}>
            <MessageSquare size={16} aria-hidden="true" />
            <span className="max-sm:hidden">Back to chat</span>
          </Link>
          <span className="max-w-56 truncate max-sm:hidden">{user.email}</span>
          <Button variant="ghost" onClick={endSession} aria-label="Log out">
            <LogOut size={16} aria-hidden="true" />
          </Button>
        </div>
      </header>
      <div className="mx-auto max-w-5xl px-5 pt-6 pb-12">{children}</div>
    </div>
  )
}
