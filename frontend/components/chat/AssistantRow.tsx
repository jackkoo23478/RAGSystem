import { Sparkles } from "lucide-react"
import type { ReactNode } from "react"

import { cn } from "@/lib/cn"

interface AssistantRowProps {
  // a quiet bubble is for messages that are not an answer (notices, the thinking indicator)
  quiet?: boolean
  role?: "status"
  children: ReactNode
}

// the avatar and the bubble that every message from the assistant sits in
export function AssistantRow({ quiet = false, role, children }: AssistantRowProps) {
  return (
    <div className="my-5 flex items-start gap-3" role={role}>
      <div className="grid size-8 flex-none place-items-center rounded-full bg-accent-soft text-accent" aria-hidden="true">
        <Sparkles size={16} />
      </div>
      <div
        className={cn(
          "min-w-0 flex-1 rounded-card rounded-tl-[4px] border border-line px-[1.1rem] py-[0.9rem]",
          quiet ? "bg-quiet" : "bg-surface shadow-card",
        )}
      >
        {children}
      </div>
    </div>
  )
}
