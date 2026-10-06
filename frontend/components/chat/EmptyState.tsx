import { Sparkles } from "lucide-react"

import styles from "./empty-state.module.css"

// examples that match the sample documents; change them to suit your own documents
const EXAMPLES = [
  "Can I get a refund?",
  "How long does shipping take?",
  "What does the warranty cover?",
]

interface EmptyStateProps {
  onPick: (question: string) => void
  disabled: boolean
}

export function EmptyState({ onPick, disabled }: EmptyStateProps) {
  return (
    <div className={styles.wrap}>
      <div className={styles.icon} aria-hidden="true">
        <Sparkles size={22} />
      </div>
      <h2 className={styles.title}>Ask about your documents</h2>
      <p className={styles.text}>Every answer comes with the passages it was based on, so you can check it.</p>
      <ul className={styles.examples} aria-label="Example questions">
        {EXAMPLES.map((example) => (
          <li key={example}>
            <button type="button" className={styles.chip} disabled={disabled} onClick={() => onPick(example)}>
              {example}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
