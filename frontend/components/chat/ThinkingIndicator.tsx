import { AssistantRow } from "./AssistantRow"

const DOT = "size-[0.45rem] rounded-full bg-muted animate-dots"

// shown while the backend is searching the documents and the language model is writing
export function ThinkingIndicator({ label }: { label: string }) {
  return (
    <AssistantRow quiet role="status">
      <div className="flex gap-[0.3rem] py-[0.35rem]" aria-hidden="true">
        <span className={DOT} />
        <span className={`${DOT} [animation-delay:0.15s]`} />
        <span className={`${DOT} [animation-delay:0.3s]`} />
      </div>
      <span className="sr-only">{label}</span>
    </AssistantRow>
  )
}
