/**
 * Shared two-column layout for Login and Register pages.
 * Left panel: branding + feature list (hidden on mobile)
 * Right panel: form card
 */
import { TrendingUp } from 'lucide-react'

const FEATURES = [
  'Upload Excel & CSV sales files',
  'Auto-detect columns — no manual mapping',
  'Revenue, product & region dashboards',
  'AI-powered sales insights',
]

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex">

      {/* ── Left branding panel ──────────────────────────────────────── */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-blue-700 to-blue-500 flex-col justify-between p-12 text-white">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-white/20 rounded-xl flex items-center justify-center">
            <TrendingUp size={20} />
          </div>
          <span className="text-lg font-bold tracking-tight">SaaS Sales BI</span>
        </div>

        <div>
          <h1 className="text-4xl font-extrabold leading-tight mb-4">
            Turn your<br />sales data into<br />decisions.
          </h1>
          <p className="text-blue-100 text-sm mb-8 max-w-xs">
            Built for Indian SMEs. Upload any Excel sheet and get instant
            dashboards — no setup, no formulas.
          </p>

          <ul className="space-y-3">
            {FEATURES.map((f) => (
              <li key={f} className="flex items-center gap-2.5 text-sm text-blue-50">
                <span className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center text-xs">✓</span>
                {f}
              </li>
            ))}
          </ul>
        </div>

        <p className="text-blue-300 text-xs">
          © {new Date().getFullYear()} SaaS Sales BI · All rights reserved
        </p>
      </div>

      {/* ── Right form panel ─────────────────────────────────────────── */}
      <div className="flex-1 flex items-center justify-center bg-gray-50 px-6 py-12">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <TrendingUp size={16} className="text-white" />
            </div>
            <span className="font-bold text-gray-900">SaaS Sales BI</span>
          </div>

          {children}
        </div>
      </div>
    </div>
  )
}
