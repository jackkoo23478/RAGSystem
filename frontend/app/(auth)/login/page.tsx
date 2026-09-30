"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import { login } from '@/lib/api/auth'
import { saveToken } from '@/lib/auth/session'

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
      setError(err instanceof Error ? err.message : "登入失敗")
    }
  }

  return (
    <main style={{ padding: '2rem' }}>
      <form onSubmit={handleSubmit(onSubmit)}>
        <input {...register('email')} placeholder="Email" />
        {errors.email && <p>{errors.email.message}</p>}

        <input {...register('password')} type="password" placeholder="Password" />
        {errors.password && <p>{errors.password.message}</p>}

        {error && <p>{error}</p>}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? '登入緊...' : '登入'}
        </button>
      </form>
    </main>
  )
}