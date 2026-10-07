"use client"

import { useId, useRef, useState } from "react"
import type { DragEvent } from "react"
import { UploadCloud } from "lucide-react"

import { Button } from "@/components/ui/Button"

import styles from "./upload-form.module.css"

const ALLOWED_EXTENSIONS = ["pdf", "txt"]

// the backend checks the type too; checking here saves a round trip and gives a clearer message
function checkFile(file: File): string | null {
  const extension = file.name.split(".").pop()?.toLowerCase() ?? ""
  if (!ALLOWED_EXTENSIONS.includes(extension)) return "Only PDF and TXT files can be uploaded."
  if (file.size === 0) return "This file is empty."
  return null
}

interface UploadFormProps {
  // resolves to true when the upload worked; on failure the file stays chosen so it can be tried again
  onUpload: (file: File, processNow: boolean) => Promise<boolean>
  disabled: boolean
}

export function UploadForm({ onUpload, disabled }: UploadFormProps) {
  const inputId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [processNow, setProcessNow] = useState(true)
  const [dragging, setDragging] = useState(false)

  const choose = (chosen: File | undefined) => {
    if (!chosen) return
    const problem = checkFile(chosen)
    setError(problem)
    setFile(problem ? null : chosen)
  }

  const onDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault()
    setDragging(false)
    if (!disabled) choose(event.dataTransfer.files[0])
  }

  const submit = async () => {
    if (!file) return
    const uploaded = await onUpload(file, processNow)
    if (!uploaded) return
    setFile(null)
    if (inputRef.current) inputRef.current.value = "" // so the same file can be chosen again
  }

  return (
    <section className={styles.card} aria-label="Upload a document">
      <label
        htmlFor={inputId}
        className={dragging ? `${styles.drop} ${styles.dragging}` : styles.drop}
        onDragOver={(event) => {
          event.preventDefault()
          if (!disabled) setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <UploadCloud size={28} aria-hidden="true" />
        <span className={styles.dropTitle}>{file ? file.name : "Choose a file or drop it here"}</span>
        <span className={styles.dropHint}>{file ? `${(file.size / 1024).toFixed(1)} KB` : "PDF or TXT"}</span>
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept=".pdf,.txt,application/pdf,text/plain"
          className={styles.input}
          disabled={disabled}
          onChange={(event) => choose(event.target.files?.[0])}
        />
      </label>

      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}

      <div className={styles.row}>
        <label className={styles.check}>
          <input type="checkbox" checked={processNow} onChange={(event) => setProcessNow(event.target.checked)} disabled={disabled} />
          Process it right after uploading
        </label>
        <Button variant="primary" onClick={submit} disabled={disabled || !file}>
          {disabled ? "Uploading..." : "Upload"}
        </Button>
      </div>
    </section>
  )
}
