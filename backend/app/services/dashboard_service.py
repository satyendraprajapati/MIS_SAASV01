"""
Dashboard aggregation service.

Returns mock data at this stage (no persistent sales table yet).
When the SalesRecord model is added in a later sprint, replace the
mock block with real SQLAlchemy queries against that table.
"""

from datetime import date
from typing import Optional
import random


def get_dashboard_data(
    db,
    start_date: Optional[date],
    end_date: Optional[date],
    products: list[str],
    regions: list[str],
) -> dict:
    """
    Aggregate KPI + chart data, applying any active filters.
    Currently returns deterministic mock data for frontend development.
    """

    # ── Mock data ────────────────────────────────────────────────────────────
    # Replace this entire block once SalesRecord ORM model + seed data exist.

    all_products = [
        "Widget A", "Widget B", "Widget C", "Widget D", "Widget E",
        "Gadget Pro", "Gadget Lite", "SuperPart", "MegaKit", "BasicBox",
        "Premium Pack", "Economy Set",
    ]
    all_regions = ["North", "South", "East", "West", "Central"]

    # Seed random so filters appear to change the numbers
    seed = (
        (start_date.toordinal() if start_date else 0)
        + (end_date.toordinal() if end_date else 0)
        + sum(ord(c) for p in products for c in p)
        + sum(ord(c) for r in regions for c in r)
    )
    rng = random.Random(seed or 42)

    active_products = products if products else all_products
    active_regions  = regions  if regions  else all_regions

    # Revenue by product (top 10)
    product_revenue = {
        p: round(rng.uniform(50_000, 500_000), 2)
        for p in active_products
    }
    top10_products = sorted(product_revenue.items(), key=lambda x: x[1], reverse=True)[:10]
    revenue_by_product = [{"product": p, "revenue": v} for p, v in top10_products]

    # Revenue trend — monthly for last 12 months
    months = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    revenue_trend = [
        {"month": m, "revenue": round(rng.uniform(80_000, 320_000), 2)}
        for m in months
    ]

    # Revenue by region
    region_revenue = {r: round(rng.uniform(100_000, 800_000), 2) for r in active_regions}
    total_region_rev = sum(region_revenue.values())
    revenue_by_region = [
        {
            "region": r,
            "revenue": v,
            "pct": round(v / total_region_rev * 100, 1),
        }
        for r, v in sorted(region_revenue.items(), key=lambda x: x[1], reverse=True)
    ]

    # KPIs
    total_revenue = sum(v for _, v in top10_products)
    total_orders  = rng.randint(200, 1500)
    avg_order_val = round(total_revenue / total_orders, 2) if total_orders else 0
    top_region    = max(region_revenue, key=region_revenue.get)

    return {
        "kpis": {
            "total_revenue":    round(total_revenue, 2),
            "total_orders":     total_orders,
            "avg_order_value":  avg_order_val,
            "top_region":       top_region,
        },
        "revenue_by_product": revenue_by_product,
        "revenue_trend":      revenue_trend,
        "revenue_by_region":  revenue_by_region,
        "filter_options": {
            "products": sorted(all_products),
            "regions":  sorted(all_regions),
        },
    }
