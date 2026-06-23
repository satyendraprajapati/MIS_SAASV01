"""
Unit tests for the column_detector module.

Three test DataFrames simulate real-world scenarios:
  DF1 — Clean, standard English headers (happy path)
  DF2 — Messy headers: mixed case, extra spaces, abbreviations, Indian numbers
  DF3 — Junk rows at top (merged Excel header), Hindi-ish column names
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import pytest
from app.services.column_detector import detect_columns, clean_header_rows


# ---------------------------------------------------------------------------
# DataFrame 1 — Clean standard English headers
# ---------------------------------------------------------------------------

DF1 = pd.DataFrame({
    "Date": pd.to_datetime(["2024-01-10", "2024-01-11", "2024-01-12",
                             "2024-01-13", "2024-01-14"]),
    "Product Name": ["Widget A", "Widget B", "Widget C", "Widget A", "Widget D"],
    "Region": ["North", "South", "East", "West", "North"],
    "Salesperson": ["Amit Kumar", "Priya Singh", "Raj Patel", "Sneha Joshi", "Arjun Mehta"],
    "Quantity": [10, 5, 8, 12, 7],
    "Unit Price": [500.0, 1200.0, 750.0, 500.0, 900.0],
    "Total Revenue": [5000.0, 6000.0, 6000.0, 6000.0, 6300.0],
})

# ---------------------------------------------------------------------------
# DataFrame 2 — Messy: abbreviations, mixed case, Indian number strings
# ---------------------------------------------------------------------------

DF2 = pd.DataFrame({
    "  INVOICE DATE ": ["15-Jan-2024", "16-Jan-2024", "17-Jan-2024",
                         "18-Jan-2024", "19-Jan-2024"],
    "item": ["Widget A", "Widget B", "Widget C", "Widget A", "Widget D"],
    "ZONE": ["North", "South", "East", "West", "North"],
    "Sales Executive": ["Amit K.", "Priya S.", "Raj P.", "Sneha J.", "Arjun M."],
    "QTY": [10, 5, 8, 12, 7],
    # Indian number formatting with ₹ symbol
    "NET AMOUNT": ["₹5,000", "₹6,000", "₹6,000", "₹6,000", "₹6,300"],
    # Extra column that has no obvious role
    "Remarks": ["OK", "Pending", "OK", "OK", "Returned"],
})

# ---------------------------------------------------------------------------
# DataFrame 3 — Junk rows at top (simulating merged Excel header export)
# ---------------------------------------------------------------------------

_raw_rows = [
    # Row 0: company name row (junk)
    ["Sharma Traders Pvt Ltd", None, None, None, None, None, None],
    # Row 1: report title row (junk)
    ["Monthly Sales Report - Jan 2024", None, None, None, None, None, None],
    # Row 2: blank row (junk)
    [None, None, None, None, None, None, None],
    # Row 3: REAL header row
    ["Tarikh", "Maal Ka Naam", "Kshetra", "Vikreta", "Matra", "Dar", "Kul Bikri"],
    # Row 4 onwards: data
    ["2024-01-10", "Product A", "Mumbai", "Ramesh", 10, 500, 5000],
    ["2024-01-11", "Product B", "Delhi", "Suresh", 5, 1200, 6000],
    ["2024-01-12", "Product C", "Chennai", "Mahesh", 8, 750, 6000],
    ["2024-01-13", "Product A", "Kolkata", "Rakesh", 12, 500, 6000],
    ["2024-01-14", "Product D", "Pune", "Dinesh", 7, 900, 6300],
]
DF3_RAW = pd.DataFrame(_raw_rows)


# ---------------------------------------------------------------------------
# Tests for DataFrame 1 — Clean headers
# ---------------------------------------------------------------------------

class TestDF1CleanHeaders:

    def setup_method(self):
        self.result = detect_columns(DF1)

    def test_date_detected(self):
        assert self.result["date"]["column"] == "Date"

    def test_date_confidence_high(self):
        assert self.result["date"]["confidence"] >= 0.7

    def test_revenue_detected(self):
        assert self.result["revenue"]["column"] == "Total Revenue"

    def test_revenue_not_unit_price(self):
        # Unit Price should NOT be picked as revenue if Total Revenue exists
        assert self.result["revenue"]["column"] != "Unit Price"

    def test_quantity_detected(self):
        assert self.result["quantity"]["column"] == "Quantity"

    def test_product_detected(self):
        assert self.result["product"]["column"] == "Product Name"

    def test_region_detected(self):
        assert self.result["region"]["column"] == "Region"

    def test_salesperson_detected(self):
        assert self.result["salesperson"]["column"] == "Salesperson"

    def test_no_column_assigned_twice(self):
        roles = ["date", "revenue", "quantity", "product", "region", "salesperson"]
        assigned = [self.result[r]["column"] for r in roles if self.result[r]["column"]]
        assert len(assigned) == len(set(assigned)), "Same column assigned to multiple roles"

    def test_undetected_has_unit_price(self):
        # Unit Price is real but ambiguous — should end up in undetected
        assert "Unit Price" in self.result["undetected"]

    def test_result_has_all_keys(self):
        required = {"date", "revenue", "quantity", "product", "region", "salesperson", "undetected"}
        assert required.issubset(self.result.keys())


# ---------------------------------------------------------------------------
# Tests for DataFrame 2 — Messy headers
# ---------------------------------------------------------------------------

class TestDF2MessyHeaders:

    def setup_method(self):
        self.result = detect_columns(DF2)

    def test_date_detected_from_invoice_date(self):
        assert self.result["date"]["column"] == "  INVOICE DATE "

    def test_revenue_detected_from_net_amount(self):
        assert self.result["revenue"]["column"] == "NET AMOUNT"

    def test_quantity_detected_from_qty(self):
        assert self.result["quantity"]["column"] == "QTY"

    def test_product_detected_from_item(self):
        assert self.result["product"]["column"] == "item"

    def test_region_detected_from_zone(self):
        assert self.result["region"]["column"] == "ZONE"

    def test_salesperson_detected_from_sales_executive(self):
        assert self.result["salesperson"]["column"] == "Sales Executive"

    def test_remarks_in_undetected(self):
        assert "Remarks" in self.result["undetected"]

    def test_all_confidences_are_valid_floats(self):
        for role in ("date", "revenue", "quantity", "product", "region", "salesperson"):
            conf = self.result[role]["confidence"]
            assert isinstance(conf, float), f"confidence for {role} is not float"
            assert 0.0 <= conf <= 1.0, f"confidence for {role} out of range: {conf}"


# ---------------------------------------------------------------------------
# Tests for DataFrame 3 — Junk header rows + Hindi-ish column names
# ---------------------------------------------------------------------------

class TestDF3JunkHeaders:

    def setup_method(self):
        # Step 1: strip junk rows to get proper header
        self.df_clean = clean_header_rows(DF3_RAW)
        # Step 2: run detection on cleaned df
        self.result = detect_columns(self.df_clean)

    def test_header_cleaning_sets_correct_columns(self):
        expected_cols = {"Tarikh", "Maal Ka Naam", "Kshetra", "Vikreta", "Matra", "Dar", "Kul Bikri"}
        assert expected_cols.issubset(set(self.df_clean.columns))

    def test_clean_df_has_data_rows(self):
        assert len(self.df_clean) == 5

    def test_date_detected_tarikh(self):
        # "Tarikh" is Hindi for date — listed in hints
        assert self.result["date"]["column"] == "Tarikh"

    def test_revenue_detected_kul_bikri(self):
        # "Kul Bikri" = Total Sales in Hindi — "bikri" in hints
        assert self.result["revenue"]["column"] == "Kul Bikri"

    def test_quantity_detected_matra(self):
        # "Matra" = quantity in Hindi
        assert self.result["quantity"]["column"] == "Matra"

    def test_region_detected_kshetra(self):
        # "Kshetra" = region in Hindi
        assert self.result["region"]["column"] == "Kshetra"

    def test_salesperson_detected_vikreta(self):
        # "Vikreta" = seller/salesperson in Hindi
        assert self.result["salesperson"]["column"] == "Vikreta"

    def test_product_detected_maal_ka_naam(self):
        # "Maal Ka Naam" = name of goods — "maal" in hints
        assert self.result["product"]["column"] == "Maal Ka Naam"


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_dataframe_returns_all_none(self):
        result = detect_columns(pd.DataFrame())
        for role in ("date", "revenue", "quantity", "product", "region", "salesperson"):
            assert result[role]["column"] is None

    def test_single_column_df(self):
        df = pd.DataFrame({"Total Revenue": [1000, 2000, 3000]})
        result = detect_columns(df)
        assert result["revenue"]["column"] == "Total Revenue"

    def test_all_numeric_df_does_not_crash(self):
        df = pd.DataFrame({
            "A": [1, 2, 3],
            "B": [4, 5, 6],
            "C": [7, 8, 9],
        })
        result = detect_columns(df)
        # Should not raise; some roles may be None
        assert "undetected" in result

    def test_duplicate_column_roles_not_assigned(self):
        """Two columns both named variations of 'revenue' — only one should be picked."""
        df = pd.DataFrame({
            "Total Revenue": [5000.0, 6000.0, 7000.0],
            "Net Revenue": [4500.0, 5500.0, 6500.0],
        })
        result = detect_columns(df)
        assigned = [result[r]["column"] for r in ("revenue",) if result[r]["column"]]
        assert len(assigned) == 1

    def test_confidence_below_threshold_returns_none(self):
        """Column with no hints and ambiguous values should not be force-assigned."""
        df = pd.DataFrame({
            "Col1": ["foo", "bar", "baz", "qux", "quux"],
            "Col2": [1, 2, 3, 4, 5],
        })
        result = detect_columns(df)
        # Neither column clearly maps to date or region
        assert result["date"]["column"] is None

    def test_clean_header_rows_no_junk(self):
        """clean_header_rows on a normal DF should return it unchanged."""
        original_cols = list(DF1.columns)
        cleaned = clean_header_rows(DF1.copy())
        assert list(cleaned.columns) == original_cols

    def test_reason_string_is_non_empty_for_detected(self):
        result = detect_columns(DF1)
        for role in ("date", "revenue", "quantity", "product", "region", "salesperson"):
            if result[role]["column"]:
                assert len(result[role]["reason"]) > 0, f"Empty reason for {role}"
