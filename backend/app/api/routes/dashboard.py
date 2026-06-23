"""
GET /api/v1/dashboard

Returns aggregated KPI and chart data for the Sales Dashboard,
with optional filters: date range, products, regions.
"""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.dashboard_service import get_dashboard_data

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("")
def dashboard(
    start_date: Optional[date] = Query(None, description="Filter from this date (YYYY-MM-DD)"),
    end_date:   Optional[date] = Query(None, description="Filter up to this date (YYYY-MM-DD)"),
    product:    Optional[list[str]] = Query(None, description="Filter by product name(s)"),
    region:     Optional[list[str]] = Query(None, description="Filter by region(s)"),
    db: Session = Depends(get_db),
):
    """
    Returns:
    - **kpis**: total_revenue, total_orders, avg_order_value, top_region
    - **revenue_by_product**: top-10 products by revenue  [{product, revenue}]
    - **revenue_trend**: monthly revenue  [{month, revenue}]
    - **revenue_by_region**: region share  [{region, revenue, pct}]
    - **filter_options**: available products and regions for dropdowns
    """
    return get_dashboard_data(
        db=db,
        start_date=start_date,
        end_date=end_date,
        products=product or [],
        regions=region or [],
    )
