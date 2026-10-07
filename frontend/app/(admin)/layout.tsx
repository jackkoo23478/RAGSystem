"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import type { ReactNode } from "react"
import { LogOut, MessageSquare } from "lucide-react"

import { Button } from "@/components/ui/Button"
import { useEndSession } from "@/hooks/useEndSession"
import { useRequireAdmin } from "@/hooks/useRequireAdmin"

import styles from "./admin-shell.module.css"

// the dashboard and logs pages are added to this list when they exist
const NAV = [{ href: "/upload", label: "Documents" }]

export default function AdminLayout({ children }: { children: ReactNode }) {
  const { user, error } = useRequireAdmin()
  const endSession = useEndSession()
  const pathname = usePathname()

  if (error) {
    return (
      <main className={styles.center}>
        <p role="alert" className={styles.error}>
          {error}
        </p>
      </main>
    )
  }

  // nothing from the admin pages is shown until the backend has confirmed the user is an admin
  if (!user) {
    return (
      <main className={styles.center}>
        <p role="status">Checking permissions…</p>
      </main>
    )
  }

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <span className={styles.brand}>Admin</span>
        <nav className={styles.nav} aria-label="Admin">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={pathname.startsWith(item.href) ? `${styles.link} ${styles.active}` : styles.link}
              aria-current={pathname.startsWith(item.href) ? "page" : undefined}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className={styles.account}>
          <Link href="/chat" className={styles.link}>
            <MessageSquare size={16} aria-hidden="true" />
            <span className={styles.linkText}>Back to chat</span>
          </Link>
          <span className={styles.email}>{user.email}</span>
          <Button variant="ghost" onClick={endSession} aria-label="Log out">
            <LogOut size={16} aria-hidden="true" />
          </Button>
        </div>
      </header>
      <div className={styles.content}>{children}</div>
    </div>
  )
}
