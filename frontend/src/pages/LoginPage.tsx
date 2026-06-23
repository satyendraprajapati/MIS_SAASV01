import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { Eye, EyeOff, Loader2, AlertCircle } from 'lucide-react'
import { loginApi, getMeApi } from '../api/auth'
import { useAuthStore } from '../store/authStore'
import AuthLayout from '../components/ui/AuthLayout'
import FormField from '../components/ui/FormField'

// ── Validation ────────────────────────────────────────────────────────────────

const schema = z.object({
  email:    z.string().email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
})
type FormData = z.infer<typeof schema>

// ── Component ─────────────────────────────────────────────────────────────────

export default function LoginPage() {
  const navigate   = useNavigate()
  const location   = useLocation()
  const setAuth    = useAuthStore((s) => s.setAuth)
  const [showPass, setShowPass] = useState(false)

  // Where to go after login (supports redirect-back after 401)
  const from = (location.state as { from?: string })?.from ?? '/dashboard'

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  // Two-step mutation: login → fetch /me → store both
  const { mutate, isPending, error } = useMutation({
    mutationFn: async (data: FormData) => {
      const tokens = await loginApi(data)
      // Immediately fetch profile so we can store user info alongside tokens
      const me = await getMeApi()
      return { tokens, me }
    },
    onSuccess: ({ tokens, me }) => {
      setAuth(tokens.access_token, tokens.refresh_token, me)
      navigate(from, { replace: true })
    },
  })

  // Extract API error message
  const apiError = (() => {
    if (!error) return null
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const detail = (error as any)?.response?.data?.detail
    if (typeof detail === 'string') return detail
    return 'Login failed. Please try again.'
  })()

  return (
    <AuthLayout>
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
        <h2 className="text-2xl font-bold text-gray-900">Welcome back</h2>
        <p className="text-sm text-gray-500 mt-1 mb-6">Sign in to your account</p>

        {/* Redirect notice (after 401 auto-logout) */}
        {location.state?.from && (
          <div className="mb-4 flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2.5 text-xs text-amber-800">
            <AlertCircle size={14} className="mt-0.5 shrink-0" />
            Your session expired. Please log in again.
          </div>
        )}

        <form onSubmit={handleSubmit((d) => mutate(d))} noValidate className="space-y-4">

          <FormField
            label="Email address"
            type="email"
            autoComplete="email"
            placeholder="you@company.com"
            error={errors.email?.message}
            {...register('email')}
          />

          <div>
            <FormField
              label="Password"
              type={showPass ? 'text' : 'password'}
              autoComplete="current-password"
              placeholder="••••••••"
              error={errors.password?.message}
              {...register('password')}
            />
            {/* show/hide toggle — sits outside FormField to avoid nested input */}
            <button
              type="button"
              onClick={() => setShowPass((s) => !s)}
              className="mt-1 text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1 transition"
              tabIndex={-1}
            >
              {showPass ? <EyeOff size={12} /> : <Eye size={12} />}
              {showPass ? 'Hide' : 'Show'} password
            </button>
          </div>

          {/* API error banner */}
          {apiError && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-lg px-3 py-2.5 text-xs text-red-700">
              <AlertCircle size={14} className="mt-0.5 shrink-0" />
              {apiError}
            </div>
          )}

          <button
            type="submit"
            disabled={isPending}
            className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold py-2.5 rounded-lg text-sm transition disabled:opacity-60 disabled:cursor-not-allowed mt-2"
          >
            {isPending && <Loader2 size={15} className="animate-spin" />}
            {isPending ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-5">
          Don't have an account?{' '}
          <Link to="/register" className="text-blue-600 hover:text-blue-800 font-medium">
            Create one
          </Link>
        </p>
      </div>
    </AuthLayout>
  )
}
