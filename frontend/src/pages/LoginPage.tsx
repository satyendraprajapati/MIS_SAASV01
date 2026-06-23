import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { loginApi } from '../api/auth'
import { useAuthStore } from '../store/authStore'

const schema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(6, 'Min 6 characters'),
})
type FormData = z.infer<typeof schema>

export default function LoginPage() {
  const navigate = useNavigate()
  const setTokens = useAuthStore((s) => s.setTokens)
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const { mutate, isPending, error } = useMutation({
    mutationFn: loginApi,
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token)
      navigate('/dashboard')
    },
  })

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-2xl shadow-lg w-full max-w-md">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">SaaS Sales BI</h1>
        <p className="text-gray-500 mb-6 text-sm">Sign in to your account</p>

        <form onSubmit={handleSubmit((d) => mutate(d))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              {...register('email')}
              type="email"
              placeholder="you@company.com"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            {errors.email && <p className="text-red-500 text-xs mt-1">{errors.email.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              {...register('password')}
              type="password"
              placeholder="••••••••"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            {errors.password && <p className="text-red-500 text-xs mt-1">{errors.password.message}</p>}
          </div>

          {error && (
            <p className="text-red-500 text-sm">Invalid email or password.</p>
          )}

          <button
            type="submit"
            disabled={isPending}
            className="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium py-2 rounded-lg text-sm transition disabled:opacity-50"
          >
            {isPending ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}
