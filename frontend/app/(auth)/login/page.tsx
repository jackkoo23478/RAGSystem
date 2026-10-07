"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { Button } from '@/components/ui/Button'
import { login } from '@/lib/api/auth'
import { saveToken } from '@/lib/auth/session'

const FIELD = 'flex flex-col gap-[0.35rem]'
const LABEL = 'text-sm font-medium'
const INPUT = 'min-h-10 rounded-control border border-line bg-page px-3 text-ink aria-[invalid=true]:border-danger'
const FIELD_ERROR = 'text-[0.8rem] text-danger'

const loginSchema = z.object({
  email: z.string().min(1, { message: "Email is required" }).email({ message: "Invalid email address" }),
  password: z.string().min(6, { message: "Password must be at least 6 characters long" }),
})

type UserFrom = z.infer<typeof loginSchema>

export default function LoginPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<UserFrom>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: UserFrom) => {
    setError(null)
    try {
      const tokens = await login(data)
      saveToken(tokens.access_token)
      router.push("/chat")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed")
    }
  }

  return (
    <main className="grid min-h-dvh place-items-center p-6">
      <form
        className="flex w-full max-w-sm flex-col gap-4 rounded-card border border-line bg-surface p-8 shadow-card"
        onSubmit={handleSubmit(onSubmit)}
        noValidate
      >
        <h1 className="text-2xl font-semibold">Document Q&A</h1>
        <p className="-mt-2 mb-2 text-muted">Log in to ask questions about your documents.</p>

        <div className={FIELD}>
          <label htmlFor="email" className={LABEL}>
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            className={INPUT}
            aria-invalid={errors.email ? "true" : undefined}
            {...register('email')}
          />
          {errors.email && <p className={FIELD_ERROR}>{errors.email.message}</p>}
        </div>

        <div className={FIELD}>
          <label htmlFor="password" className={LABEL}>
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            className={INPUT}
            aria-invalid={errors.password ? "true" : undefined}
            {...register('password')}
          />
          {errors.password && <p className={FIELD_ERROR}>{errors.password.message}</p>}
        </div>

        {error && (
          <p role="alert" className="rounded-control bg-danger-soft px-3 py-[0.6rem] text-[0.9rem] text-danger">
            {error}
          </p>
        )}

        <Button type="submit" variant="primary" fullWidth disabled={isSubmitting}>
          {isSubmitting ? 'Logging in...' : 'Log in'}
        </Button>
      </form>
    </main>
  )
}
