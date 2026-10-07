import { cn } from "@/lib/cn"

// the links in the page headers: the same on the chat page and in the admin area
export function headerLink(active = false): string {
  return cn(
    "inline-flex items-center gap-[0.4rem] rounded-control px-3 py-[0.4rem] no-underline",
    active ? "bg-accent-soft text-accent" : "text-ink hover:bg-surface-2",
  )
}
