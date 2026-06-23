import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar,
  LineChart, Line,
  PieChart, Pie, Cell, Sector,
  XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer,
} from 'recharts'
import {
  TrendingUp, ShoppingCart, Calculator,
  MapPin, RefreshCw, AlertCircle, Filter,
} from 'lucide-react'
import { useState, useCallback } from 'react'
import { fetchDashboard, DashboardFilters, FilterOptions } from '../api/dashboard'
import { useAuthStore } from '../store/authStore'
import { useNavigate } from 'react-router-dom'

// ─── Palette ──────────────────────────────────────────────────────────────────
const CHART_COLORS = ['#2563eb', '#7c3aed', '#db2777', '#ea580c', '#16a34a',
                      '#0891b2', '#d97706', '#9333ea', '#dc2626', '#65a30d']
const REGION_COLORS: Record<string, string> = {
  North:   '#2563eb',
  South:   '#16a34a',
  East:    '#ea580c',
  West:    '#7c3aed',
  Central: '#0891b2',
}
const regionColor = (name: string, idx: number) =>
  REGION_COLORS[name] ?? CHART_COLORS[idx % CHART_COLORS.length]

// ─── Formatters ───────────────────────────────────────────────────────────────
const fmt = {
  currency: (v: number) =>
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(v),
  compact: (v: number) => {
    if (v >= 1_00_00_000) return `₹${(v / 1_00_00_000).toFixed(1)}Cr`
    if (v >= 1_00_000)    return `₹${(v / 1_00_000).toFixed(1)}L`
    if (v >= 1_000)       return `₹${(v / 1_000).toFixed(1)}K`
    return `₹${v}`
  },
  number: (v: number) => new Intl.NumberFormat('en-IN').format(v),
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────
interface KpiCardProps {
  label: string
  value: string
  sub?: string
  icon: React.ReactNode
  accent: string   // tailwind bg class for icon container
  trend?: number   // optional % change (positive = good)
}

function KpiCard({ label, value, sub, icon, accent, trend }: KpiCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 flex gap-4 items-start">
      <div className={`${accent} rounded-lg p-2.5 mt-0.5 shrink-0`}>{icon}</div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide truncate">{label}</p>
        <p className="text-2xl font-bold text-gray-900 mt-0.5 truncate">{value}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
        {trend !== undefined && (
          <p className={`text-xs font-medium mt-1 ${trend >= 0 ? 'text-green-600' : 'text-red-500'}`}>
            {trend >= 0 ? '▲' : '▼'} {Math.abs(trend).toFixed(1)}% vs last period
          </p>
        )}
      </div>
    </div>
  )
}

// ─── Multi-select dropdown ────────────────────────────────────────────────────
interface MultiSelectProps {
  label: string
  options: string[]
  selected: string[]
  onChange: (v: string[]) => void
}

function MultiSelect({ label, options, selected, onChange }: MultiSelectProps) {
  const [open, setOpen] = useState(false)

  const toggle = (opt: string) => {
    onChange(selected.includes(opt) ? selected.filter((s) => s !== opt) : [...selected, opt])
  }

  const displayText = selected.length === 0
    ? `All ${label}s`
    : selected.length === 1
      ? selected[0]
      : `${selected.length} ${label}s`

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 bg-white border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 hover:border-blue-400 transition min-w-[150px] shadow-sm"
      >
        <Filter size={13} className="text-gray-400" />
        <span className="flex-1 text-left truncate">{displayText}</span>
        <span className="text-gray-400 text-xs">{open ? '▲' : '▼'}</span>
      </button>

      {open && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute top-full mt-1 left-0 z-20 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[190px] max-h-60 overflow-y-auto">
            {/* Clear all */}
            {selected.length > 0 && (
              <button
                onClick={() => { onChange([]); setOpen(false) }}
                className="w-full text-left px-3 py-1.5 text-xs text-blue-600 hover:bg-blue-50 font-medium"
              >
                Clear all
              </button>
            )}
            {options.map((opt) => (
              <label
                key={opt}
                className="flex items-center gap-2.5 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selected.includes(opt)}
                  onChange={() => toggle(opt)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                {opt}
              </label>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

// ─── Custom tooltip (reused across charts) ────────────────────────────────────
interface TooltipPayload { name: string; value: number; color?: string }

function ChartTooltip({ active, payload, label }: {
  active?: boolean; payload?: TooltipPayload[]; label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg px-3 py-2 text-sm">
      {label && <p className="font-semibold text-gray-700 mb-1">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color ?? '#2563eb' }}>
          {p.name}: <span className="font-bold">{fmt.currency(p.value)}</span>
        </p>
      ))}
    </div>
  )
}

// ─── Active pie slice renderer ────────────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const renderActiveShape = (props: any) => {
  const { cx, cy, innerRadius, outerRadius, startAngle, endAngle,
          fill, payload, percent, value } = props
  return (
    <g>
      <text x={cx} y={cy - 10} textAnchor="middle" fill="#111827" className="text-sm font-bold" fontSize={14}>
        {payload.region}
      </text>
      <text x={cx} y={cy + 10} textAnchor="middle" fill="#6b7280" fontSize={12}>
        {fmt.compact(value)}
      </text>
      <text x={cx} y={cy + 28} textAnchor="middle" fill="#9ca3af" fontSize={11}>
        {(percent * 100).toFixed(1)}%
      </text>
      <Sector cx={cx} cy={cy} innerRadius={innerRadius} outerRadius={outerRadius + 8}
              startAngle={startAngle} endAngle={endAngle} fill={fill} />
      <Sector cx={cx} cy={cy} innerRadius={outerRadius + 12} outerRadius={outerRadius + 14}
              startAngle={startAngle} endAngle={endAngle} fill={fill} />
    </g>
  )
}

// ─── Chart card wrapper ───────────────────────────────────────────────────────
function ChartCard({ title, subtitle, children }: {
  title: string; subtitle?: string; children: React.ReactNode
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-gray-800">{title}</h3>
        {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

// ─── Skeleton loader ──────────────────────────────────────────────────────────
function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse bg-gray-100 rounded-lg ${className}`} />
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24" />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Skeleton className="h-72" />
        <Skeleton className="h-72" />
      </div>
      <Skeleton className="h-72" />
    </div>
  )
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────
export default function DashboardPage() {
  const logout   = useAuthStore((s) => s.logout)
  const navigate = useNavigate()

  // Filter state
  const [startDate,    setStartDate]    = useState('')
  const [endDate,      setEndDate]      = useState('')
  const [selProducts,  setSelProducts]  = useState<string[]>([])
  const [selRegions,   setSelRegions]   = useState<string[]>([])
  const [activePieIdx, setActivePieIdx] = useState(0)

  const filters: DashboardFilters = {
    ...(startDate && { start_date: startDate }),
    ...(endDate   && { end_date:   endDate   }),
    ...(selProducts.length && { product: selProducts }),
    ...(selRegions.length  && { region:  selRegions  }),
  }

  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ['dashboard', filters],
    queryFn:  () => fetchDashboard(filters),
    staleTime: 1000 * 60 * 5,
  })

  const filterOptions: FilterOptions = data?.filter_options ?? { products: [], regions: [] }

  const clearFilters = useCallback(() => {
    setStartDate('')
    setEndDate('')
    setSelProducts([])
    setSelRegions([])
  }, [])

  const hasFilters = startDate || endDate || selProducts.length || selRegions.length

  // ── Error state ────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center space-y-3">
          <AlertCircle className="mx-auto text-red-400" size={40} />
          <p className="text-gray-600 font-medium">Failed to load dashboard data</p>
          <button
            onClick={() => refetch()}
            className="text-sm text-blue-600 hover:underline"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">

      {/* ── Top nav ─────────────────────────────────────────────────────── */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 bg-blue-600 rounded-md flex items-center justify-center">
            <TrendingUp size={14} className="text-white" />
          </div>
          <span className="text-sm font-semibold text-gray-800">SaaS Sales BI</span>
          <span className="hidden sm:block text-gray-300 text-sm">|</span>
          <span className="hidden sm:block text-xs text-gray-400">Sales Dashboard</span>
        </div>
        <div className="flex items-center gap-3">
          {isFetching && !isLoading && (
            <span className="text-xs text-gray-400 flex items-center gap-1">
              <RefreshCw size={11} className="animate-spin" /> Refreshing
            </span>
          )}
          <button
            onClick={() => { logout(); navigate('/login') }}
            className="text-xs text-gray-500 hover:text-gray-800 transition"
          >
            Sign out
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">

        {/* ── Page title ──────────────────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Sales Overview</h1>
            <p className="text-xs text-gray-400 mt-0.5">
              {data ? `Showing ${fmt.number(data.kpis.total_orders)} orders` : 'Loading data…'}
            </p>
          </div>
          <button
            onClick={() => refetch()}
            className="self-start sm:self-auto flex items-center gap-1.5 text-xs text-gray-500 hover:text-blue-600 border border-gray-200 rounded-lg px-3 py-1.5 bg-white shadow-sm hover:border-blue-300 transition"
          >
            <RefreshCw size={12} /> Refresh
          </button>
        </div>

        {/* ── Filter bar ──────────────────────────────────────────────────── */}
        <div className="bg-white border border-gray-100 rounded-xl shadow-sm px-4 py-3">
          <div className="flex flex-wrap items-end gap-3">

            {/* Date range */}
            <div className="flex items-end gap-2">
              <div>
                <label className="block text-xs text-gray-500 mb-1 font-medium">From</label>
                <input
                  type="date"
                  value={startDate}
                  max={endDate || undefined}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1 font-medium">To</label>
                <input
                  type="date"
                  value={endDate}
                  min={startDate || undefined}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
                />
              </div>
            </div>

            {/* Product + Region multi-selects */}
            <div className="flex items-end gap-2 flex-wrap">
              <div>
                <label className="block text-xs text-gray-500 mb-1 font-medium">Product</label>
                <MultiSelect
                  label="Product"
                  options={filterOptions.products}
                  selected={selProducts}
                  onChange={setSelProducts}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1 font-medium">Region</label>
                <MultiSelect
                  label="Region"
                  options={filterOptions.regions}
                  selected={selRegions}
                  onChange={setSelRegions}
                />
              </div>
            </div>

            {/* Clear */}
            {hasFilters && (
              <button
                onClick={clearFilters}
                className="self-end text-xs text-blue-600 hover:text-blue-800 font-medium pb-2.5"
              >
                Clear filters
              </button>
            )}
          </div>

          {/* Active filter pills */}
          {hasFilters && (
            <div className="flex flex-wrap gap-1.5 mt-2.5 pt-2.5 border-t border-gray-100">
              {startDate && (
                <span className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-full">
                  From: {startDate}
                  <button onClick={() => setStartDate('')} className="hover:text-blue-900">×</button>
                </span>
              )}
              {endDate && (
                <span className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded-full">
                  To: {endDate}
                  <button onClick={() => setEndDate('')} className="hover:text-blue-900">×</button>
                </span>
              )}
              {selProducts.map((p) => (
                <span key={p} className="inline-flex items-center gap-1 bg-violet-50 text-violet-700 text-xs px-2 py-0.5 rounded-full">
                  {p}
                  <button onClick={() => setSelProducts(selProducts.filter((x) => x !== p))} className="hover:text-violet-900">×</button>
                </span>
              ))}
              {selRegions.map((r) => (
                <span key={r} className="inline-flex items-center gap-1 bg-green-50 text-green-700 text-xs px-2 py-0.5 rounded-full">
                  {r}
                  <button onClick={() => setSelRegions(selRegions.filter((x) => x !== r))} className="hover:text-green-900">×</button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* ── Content ─────────────────────────────────────────────────────── */}
        {isLoading ? <DashboardSkeleton /> : data && (
          <>
            {/* KPI row */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard
                label="Total Revenue"
                value={fmt.compact(data.kpis.total_revenue)}
                sub={fmt.currency(data.kpis.total_revenue)}
                icon={<TrendingUp size={18} className="text-blue-600" />}
                accent="bg-blue-50"
              />
              <KpiCard
                label="Total Orders"
                value={fmt.number(data.kpis.total_orders)}
                sub="transactions"
                icon={<ShoppingCart size={18} className="text-violet-600" />}
                accent="bg-violet-50"
              />
              <KpiCard
                label="Avg Order Value"
                value={fmt.compact(data.kpis.avg_order_value)}
                sub={fmt.currency(data.kpis.avg_order_value)}
                icon={<Calculator size={18} className="text-orange-500" />}
                accent="bg-orange-50"
              />
              <KpiCard
                label="Top Region"
                value={data.kpis.top_region}
                sub="by revenue"
                icon={<MapPin size={18} className="text-green-600" />}
                accent="bg-green-50"
              />
            </div>

            {/* Chart row 1 — Bar + Pie */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">

              {/* Bar chart — Revenue by Product */}
              <div className="lg:col-span-3">
                <ChartCard
                  title="Revenue by Product"
                  subtitle="Top 10 products by total revenue"
                >
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart
                      data={data.revenue_by_product}
                      layout="vertical"
                      margin={{ left: 8, right: 24, top: 4, bottom: 4 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                      <XAxis
                        type="number"
                        tickFormatter={fmt.compact}
                        tick={{ fontSize: 11, fill: '#9ca3af' }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        type="category"
                        dataKey="product"
                        width={80}
                        tick={{ fontSize: 11, fill: '#6b7280' }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        content={<ChartTooltip />}
                        formatter={(v: number) => [fmt.currency(v), 'Revenue']}
                        cursor={{ fill: '#f8fafc' }}
                      />
                      <Bar dataKey="revenue" name="Revenue" radius={[0, 4, 4, 0]}>
                        {data.revenue_by_product.map((_, i) => (
                          <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </ChartCard>
              </div>

              {/* Pie chart — Revenue by Region */}
              <div className="lg:col-span-2">
                <ChartCard
                  title="Revenue by Region"
                  subtitle="Click a slice to highlight"
                >
                  <ResponsiveContainer width="100%" height={280}>
                    <PieChart>
                      <Pie
                        activeIndex={activePieIdx}
                        activeShape={renderActiveShape}
                        data={data.revenue_by_region}
                        dataKey="revenue"
                        nameKey="region"
                        cx="50%"
                        cy="50%"
                        innerRadius={62}
                        outerRadius={88}
                        onMouseEnter={(_, index) => setActivePieIdx(index)}
                      >
                        {data.revenue_by_region.map((entry, i) => (
                          <Cell key={entry.region} fill={regionColor(entry.region, i)} />
                        ))}
                      </Pie>
                      <Legend
                        iconType="circle"
                        iconSize={8}
                        formatter={(value) => (
                          <span className="text-xs text-gray-600">{value}</span>
                        )}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </ChartCard>
              </div>
            </div>

            {/* Line chart — Revenue Trend */}
            <ChartCard
              title="Revenue Trend"
              subtitle="Monthly revenue over the last 12 months"
            >
              <ResponsiveContainer width="100%" height={240}>
                <LineChart
                  data={data.revenue_trend}
                  margin={{ left: 8, right: 24, top: 8, bottom: 4 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 11, fill: '#9ca3af' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tickFormatter={fmt.compact}
                    tick={{ fontSize: 11, fill: '#9ca3af' }}
                    axisLine={false}
                    tickLine={false}
                    width={52}
                  />
                  <Tooltip
                    content={<ChartTooltip />}
                    formatter={(v: number) => [fmt.currency(v), 'Revenue']}
                  />
                  <Line
                    type="monotone"
                    dataKey="revenue"
                    name="Revenue"
                    stroke="#2563eb"
                    strokeWidth={2.5}
                    dot={{ r: 3, fill: '#2563eb', strokeWidth: 0 }}
                    activeDot={{ r: 5, fill: '#2563eb' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>

            {/* Region summary table */}
            <ChartCard
              title="Region Breakdown"
              subtitle="Revenue and share per region"
            >
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="text-left text-xs font-medium text-gray-400 pb-2 pr-4">Region</th>
                      <th className="text-right text-xs font-medium text-gray-400 pb-2 pr-4">Revenue</th>
                      <th className="text-right text-xs font-medium text-gray-400 pb-2 w-32">Share</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.revenue_by_region.map((row, i) => (
                      <tr key={row.region} className="border-b border-gray-50 last:border-0">
                        <td className="py-2.5 pr-4">
                          <div className="flex items-center gap-2">
                            <span
                              className="w-2.5 h-2.5 rounded-full shrink-0"
                              style={{ background: regionColor(row.region, i) }}
                            />
                            <span className="font-medium text-gray-700">{row.region}</span>
                          </div>
                        </td>
                        <td className="py-2.5 pr-4 text-right font-medium text-gray-800">
                          {fmt.currency(row.revenue)}
                        </td>
                        <td className="py-2.5">
                          <div className="flex items-center justify-end gap-2">
                            <div className="flex-1 max-w-[80px] bg-gray-100 rounded-full h-1.5">
                              <div
                                className="h-1.5 rounded-full"
                                style={{
                                  width: `${row.pct}%`,
                                  background: regionColor(row.region, i),
                                }}
                              />
                            </div>
                            <span className="text-xs text-gray-500 w-10 text-right">{row.pct}%</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </ChartCard>

          </>
        )}
      </main>
    </div>
  )
}
