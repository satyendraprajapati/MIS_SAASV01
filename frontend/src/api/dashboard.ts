import api from './client'

export interface KPIs {
  total_revenue: number
  total_orders: number
  avg_order_value: number
  top_region: string
}

export interface ProductRevenue {
  product: string
  revenue: number
}

export interface RevenueTrend {
  month: string
  revenue: number
}

export interface RegionRevenue {
  region: string
  revenue: number
  pct: number
}

export interface FilterOptions {
  products: string[]
  regions: string[]
}

export interface DashboardData {
  kpis: KPIs
  revenue_by_product: ProductRevenue[]
  revenue_trend: RevenueTrend[]
  revenue_by_region: RegionRevenue[]
  filter_options: FilterOptions
}

export interface DashboardFilters {
  start_date?: string
  end_date?: string
  product?: string[]
  region?: string[]
}

export const fetchDashboard = (filters: DashboardFilters = {}): Promise<DashboardData> => {
  const params = new URLSearchParams()
  if (filters.start_date) params.set('start_date', filters.start_date)
  if (filters.end_date)   params.set('end_date',   filters.end_date)
  filters.product?.forEach((p) => params.append('product', p))
  filters.region?.forEach((r)  => params.append('region',  r))
  return api.get<DashboardData>(`/dashboard?${params.toString()}`).then((r) => r.data)
}
