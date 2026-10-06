"use client"

import { useEffect, useRef } from "react"
import type { KeyboardEvent } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { SendHorizontal } from "lucide-react"
import { z } from "zod"

import { Button } from "@/components/ui/Button"

import styles from "./composer.module.css"

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
    <div className={styles.bar}>
      <form className={styles.form} onSubmit={submit}>
        <textarea
          {...field}
          ref={(element) => {
            registerRef(element)
            inputRef.current = element
          }}
          className={styles.input}
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
        <p role="alert" className={styles.error}>
          {errors.question.message}
        </p>
      ) : (
        <p className={styles.hint}>Enter to send, Shift+Enter for a new line</p>
      )}
    </div>
  )
}
