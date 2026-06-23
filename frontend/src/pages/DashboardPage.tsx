import { useAuthStore } from '../store/authStore'
import { useNavigate } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const sampleData = [
  { month: 'Jan', revenue: 42000 },
  { month: 'Feb', revenue: 53000 },
  { month: 'Mar', revenue: 61000 },
  { month: 'Apr', revenue: 55000 },
  { month: 'May', revenue: 78000 },
  { month: 'Jun', revenue: 91000 },
]

export default function DashboardPage() {
  const logout = useAuthStore((s) => s.logout)
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
        <h1 className="text-lg font-semibold text-gray-900">SaaS Sales BI</h1>
        <button
          onClick={handleLogout}
          className="text-sm text-gray-500 hover:text-gray-800 transition"
        >
          Sign out
        </button>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Revenue Overview</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {[
            { label: 'Total Revenue', value: '$380,000' },
            { label: 'Active Deals', value: '24' },
            { label: 'Win Rate', value: '67%' },
          ].map((stat) => (
            <div key={stat.label} className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
              <p className="text-sm text-gray-500">{stat.label}</p>
              <p className="text-3xl font-bold text-gray-900 mt-1">{stat.value}</p>
            </div>
          ))}
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-base font-semibold text-gray-700 mb-4">Monthly Revenue</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={sampleData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v: number) => `$${v.toLocaleString()}`} />
              <Bar dataKey="revenue" fill="#2563eb" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </main>
    </div>
  )
}
