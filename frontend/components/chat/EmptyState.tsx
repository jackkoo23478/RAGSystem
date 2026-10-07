import { Sparkles } from "lucide-react"

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
    <div className="flex flex-col items-center px-4 pt-16 pb-8 text-center">
      <div className="mb-4 grid size-12 place-items-center rounded-full bg-accent-soft text-accent" aria-hidden="true">
        <Sparkles size={22} />
      </div>
      <h2 className="text-[1.35rem] font-semibold">Ask about your documents</h2>
      <p className="mt-2 mb-6 max-w-[28rem] text-muted">Every answer comes with the passages it was based on, so you can check it.</p>
      <ul className="flex flex-wrap justify-center gap-2" aria-label="Example questions">
        {EXAMPLES.map((example) => (
          <li key={example}>
            <button
              type="button"
              className="cursor-pointer rounded-full border border-line bg-surface px-[0.9rem] py-2 text-[0.9rem] text-ink transition-[border-color,background-color] duration-150 enabled:hover:border-accent enabled:hover:bg-accent-soft disabled:cursor-not-allowed disabled:opacity-50"
              disabled={disabled}
              onClick={() => onPick(example)}
            >
              {example}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
