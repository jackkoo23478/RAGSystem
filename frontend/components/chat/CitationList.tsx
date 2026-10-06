import { ChevronRight, FileText } from "lucide-react"

import type { Citation } from "@/lib/types/rag"

import styles from "./chat.module.css"

// The snippet comes from an uploaded document, so it is untrusted text.
// It is only ever rendered as text (React escapes it); never use dangerouslySetInnerHTML here.
export function CitationList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null

  return (
    <section className={styles.sources} aria-label="Sources">
      <h3 className={styles.sourcesTitle}>Sources</h3>
      <ul className={styles.citations}>
        {citations.map((citation, index) => (
          <li key={`${citation.document_id ?? citation.document_name}-${index}`}>
            <details className={styles.citation}>
              <summary>
                <ChevronRight size={14} className={styles.chevron} aria-hidden="true" />
                <FileText size={16} className={styles.fileIcon} aria-hidden="true" />
                {citation.number !== null && <span className={styles.badge}>{citation.number}</span>}
                <span className={styles.source}>{citation.document_name}</span>
                {citation.page_number !== null && <span className={styles.page}>· page {citation.page_number}</span>}
              </summary>
              <blockquote className={styles.snippet}>{citation.snippet}</blockquote>
            </details>
          </li>
        ))}
      </ul>
    </section>
  )
}
