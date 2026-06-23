import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { Eye, EyeOff, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react'
import { registerApi, loginApi, getMeApi } from '../api/auth'
import { useAuthStore } from '../store/authStore'
import AuthLayout from '../components/ui/AuthLayout'
import FormField from '../components/ui/FormField'

// ── Validation (mirrors backend rules) ───────────────────────────────────────

const schema = z.object({
  full_name:    z.string().min(1, 'Full name is required').max(100),
  company_name: z.string().max(100).optional(),
  email:        z.string().email('Enter a valid email address'),
  password: z
    .string()
    .min(8,  'At least 8 characters')
    .regex(/[A-Z]/, 'Must contain an uppercase letter')
    .regex(/[0-9]/, 'Must contain a number'),
  confirm_password: z.string(),
}).refine((d) => d.password === d.confirm_password, {
  message: 'Passwords do not match',
  path: ['confirm_password'],
})

type FormData = z.infer<typeof schema>

// ── Password strength indicator ───────────────────────────────────────────────

function PasswordStrength({ password }: { password: string }) {
  const checks = [
    { label: '8+ characters', ok: password.length >= 8 },
    { label: 'Uppercase letter', ok: /[A-Z]/.test(password) },
    { label: 'Number', ok: /[0-9]/.test(password) },
  ]
  if (!password) return null
  return (
    <div className="mt-1.5 flex gap-3">
      {checks.map((c) => (
        <span
          key={c.label}
          className={`flex items-center gap-1 text-xs ${c.ok ? 'text-green-600' : 'text-gray-400'}`}
        >
          <CheckCircle2 size={11} className={c.ok ? 'text-green-500' : 'text-gray-300'} />
          {c.label}
        </span>
      ))}
    </div>
  )
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function RegisterPage() {
  const navigate  = useNavigate()
  const setAuth   = useAuthStore((s) => s.setAuth)
  const [showPass, setShowPass] = useState(false)

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema), mode: 'onChange' })

  const passwordValue = watch('password', '')

  const { mutate, isPending, error } = useMutation({
    mutationFn: async (data: FormData) => {
      // Register → auto-login → fetch /me (no extra click required)
      await registerApi({
        email:        data.email,
        password:     data.password,
        full_name:    data.full_name,
        company_name: data.company_name || undefined,
      })
      const tokens = await loginApi({ email: data.email, password: data.password })
      const me     = await getMeApi()
      return { tokens, me }
    },
    onSuccess: ({ tokens, me }) => {
      setAuth(tokens.access_token, tokens.refresh_token, me)
      navigate('/dashboard', { replace: true })
    },
  })

  const apiError = (() => {
    if (!error) return null
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const raw = (error as any)?.response?.data?.detail
    if (typeof raw === 'string') return raw
    if (Array.isArray(raw)) return raw.map((e: { msg: string }) => e.msg).join('. ')
    return 'Registration failed. Please try again.'
  })()

  return (
    <AuthLayout>
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
        <h2 className="text-2xl font-bold text-gray-900">Create your account</h2>
        <p className="text-sm text-gray-500 mt-1 mb-6">Start analysing your sales data today</p>

        <form onSubmit={handleSubmit((d) => mutate(d))} noValidate className="space-y-4">

          {/* Row: full name + company */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <FormField
              label="Full name"
              type="text"
              autoComplete="name"
              placeholder="Amit Kumar"
              error={errors.full_name?.message}
              {...register('full_name')}
            />
            <FormField
              label="Company name"
              type="text"
              autoComplete="organization"
              placeholder="Sharma Traders (optional)"
              error={errors.company_name?.message}
              {...register('company_name')}
            />
          </div>

          <FormField
            label="Work email"
            type="email"
            autoComplete="email"
            placeholder="amit@company.com"
            error={errors.email?.message}
            {...register('email')}
          />

          <div>
            <FormField
              label="Password"
              type={showPass ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="Min. 8 characters"
              error={errors.password?.message}
              hint={!errors.password ? 'At least 8 chars, one uppercase, one number' : undefined}
              {...register('password')}
            />
            <div className="flex items-center justify-between mt-1">
              <PasswordStrength password={passwordValue} />
              <button
                type="button"
                onClick={() => setShowPass((s) => !s)}
                className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1 transition"
                tabIndex={-1}
              >
                {showPass ? <EyeOff size={12} /> : <Eye size={12} />}
                {showPass ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>

          <FormField
            label="Confirm password"
            type={showPass ? 'text' : 'password'}
            autoComplete="new-password"
            placeholder="Re-enter password"
            error={errors.confirm_password?.message}
            {...register('confirm_password')}
          />

          {/* API error */}
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
            {isPending ? 'Creating account…' : 'Create account'}
          </button>

          <p className="text-xs text-gray-400 text-center">
            By signing up you agree to our Terms of Service and Privacy Policy.
          </p>
        </form>

        <p className="text-center text-sm text-gray-500 mt-5">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-600 hover:text-blue-800 font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </AuthLayout>
  )
}
