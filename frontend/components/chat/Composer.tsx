"use client"

import { useEffect, useRef } from "react"
import type { KeyboardEvent } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { SendHorizontal } from "lucide-react"
import { z } from "zod"

import { Button } from "@/components/ui/Button"

// same limits as the backend (QueryRequest): 1 to 1000 characters after trimming
const questionSchema = z.object({
  question: z
    .string()
    .trim()
    .min(1, { message: "Please enter a question" })
    .max(1000, { message: "Questions can be at most 1000 characters" }),
})

type QuestionForm = z.infer<typeof questionSchema>

interface ComposerProps {
  onSend: (question: string) => void
  disabled: boolean
}

export function Composer({ onSend, disabled }: ComposerProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<QuestionForm>({
    resolver: zodResolver(questionSchema),
  })

  // keep our own ref next to react-hook-form's, so the box can take focus back after an answer arrives
  const { ref: registerRef, ...field } = register("question")
  const inputRef = useRef<HTMLTextAreaElement | null>(null)
  const wasDisabled = useRef(disabled)
  useEffect(() => {
    if (wasDisabled.current && !disabled) inputRef.current?.focus()
    wasDisabled.current = disabled
  }, [disabled])

  const submit = handleSubmit(({ question }) => {
    reset()
    onSend(question)
  })

  // Enter sends, Shift+Enter adds a new line.
  // isComposing: while an input method (Chinese, Japanese...) is choosing characters, Enter confirms them and must not send.
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div className="bg-page px-5 pt-3 pb-4">
      <form
        className="mx-auto flex max-w-[46rem] items-end gap-2 rounded-card border border-line bg-surface p-2 shadow-card focus-within:border-accent"
        onSubmit={submit}
      >
        <textarea
          {...field}
          ref={(element) => {
            registerRef(element)
            inputRef.current = element
          }}
          // field-sizing-content: the box grows with the text where the browser supports it
          className="max-h-36 min-w-0 flex-1 resize-none bg-transparent px-[0.6rem] py-2 text-ink outline-none field-sizing-content placeholder:text-muted"
          rows={1}
          aria-label="Your question"
          placeholder="Ask about your documents"
          disabled={disabled}
          autoComplete="off"
          onKeyDown={onKeyDown}
        />
        <Button type="submit" variant="primary" disabled={disabled} aria-label="Send question">
          <SendHorizontal size={18} aria-hidden="true" />
        </Button>
      </form>
      {errors.question ? (
        <p role="alert" className="mx-auto mt-[0.4rem] max-w-[46rem] px-2 text-[0.8rem] text-danger">
          {errors.question.message}
        </p>
      ) : (
        // the keyboard shortcut hint means nothing on a touch screen
        <p className="mx-auto mt-[0.4rem] max-w-[46rem] px-2 text-[0.8rem] text-muted [@media(hover:none)]:hidden">
          Enter to send, Shift+Enter for a new line
        </p>
      )}
    </div>
  )
}
