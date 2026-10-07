import { ChevronRight, FileText } from "lucide-react"

import type { Citation } from "@/lib/types/rag"

// The snippet comes from an uploaded document, so it is untrusted text.
// It is only ever rendered as text (React escapes it); never use dangerouslySetInnerHTML here.
export function CitationList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null

  return (
    <section className="mt-4 border-t border-line pt-3" aria-label="Sources">
      <h3 className="mb-2 text-xs font-semibold tracking-wider text-muted uppercase">Sources</h3>
      <ul className="flex flex-col gap-[0.4rem]">
        {citations.map((citation, index) => (
          <li key={`${citation.document_id ?? citation.document_name}-${index}`}>
            <details className="group rounded-control bg-surface-2">
              {/* list-none and the webkit rule hide the default triangle: the chevron replaces it */}
              <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2 text-sm [&::-webkit-details-marker]:hidden">
                <ChevronRight
                  size={14}
                  className="flex-none text-muted transition-transform duration-150 group-open:rotate-90"
                  aria-hidden="true"
                />
                <FileText size={16} className="flex-none text-muted" aria-hidden="true" />
                {citation.number !== null && (
                  <span className="flex-none rounded-full bg-accent-soft px-[0.4rem] text-xs font-semibold text-accent">{citation.number}</span>
                )}
                <span className="min-w-0 truncate">{citation.document_name}</span>
                {citation.page_number !== null && <span className="flex-none text-muted">· page {citation.page_number}</span>}
              </summary>
              <blockquote className="pt-1 pr-3 pb-3 pl-[2.4rem] text-sm wrap-anywhere whitespace-pre-wrap text-muted">{citation.snippet}</blockquote>
            </details>
          </li>
        ))}
      </ul>
    </section>
  )
}
