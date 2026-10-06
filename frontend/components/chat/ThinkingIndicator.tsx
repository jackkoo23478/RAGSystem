import { Sparkles } from "lucide-react"

import styles from "./chat.module.css"

// shown while the backend is searching the documents and the language model is writing
export function ThinkingIndicator({ label }: { label: string }) {
  return (
    <div className={styles.row} role="status">
      <div className={styles.avatar} aria-hidden="true">
        <Sparkles size={16} />
      </div>
      <div className={`${styles.bubble} ${styles.bubbleQuiet}`}>
        <div className={styles.dots} aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <span className={styles.srOnly}>{label}</span>
      </div>
    </div>
  )
}
