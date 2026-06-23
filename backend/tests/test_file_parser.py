"""
Quick smoke-test for the file_parser service.
Run from backend/ directory:  python -m pytest tests/ -v
"""

import io
import json
import pandas as pd
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.file_parser import parse_and_clean


def _make_csv(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


def _make_xlsx(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


SAMPLE_ROWS = [
    {"Date": "2024-01-15", "Product Name": "  Widget A  ", "Region": "North",
     "Salesperson": "Amit Kumar", "Quantity": "10", "Unit Price": "500", "Total Revenue": "5000"},
    {"Date": "2024-01-16", "Product Name": "Widget B", "Region": "South",
     "Salesperson": "Priya Singh", "Quantity": "5", "Unit Price": "1,200", "Total Revenue": "6,000"},
    # Duplicate row
    {"Date": "2024-01-16", "Product Name": "Widget B", "Region": "South",
     "Salesperson": "Priya Singh", "Quantity": "5", "Unit Price": "1,200", "Total Revenue": "6,000"},
    # Row with nulls
    {"Date": None, "Product Name": "Widget C", "Region": None,
     "Salesperson": "Raj Patel", "Quantity": "8", "Unit Price": "750", "Total Revenue": "6000"},
    {"Date": "2024-01-18", "Product Name": "Widget D", "Region": "East",
     "Salesperson": "Sneha Joshi", "Quantity": "12", "Unit Price": "300", "Total Revenue": "3600"},
    {"Date": "2024-01-19", "Product Name": "Widget E", "Region": "West",
     "Salesperson": "Arjun Mehta", "Quantity": "7", "Unit Price": "900", "Total Revenue": "6300"},
]


class TestCSVParsing:
    def test_basic_parse(self):
        result = parse_and_clean(_make_csv(SAMPLE_ROWS), "sales.csv")
        assert result["row_count"] == 5          # duplicate removed
        assert result["duplicates_removed"] == 1
        assert "Date" in result["columns"]

    def test_schema_detection(self):
        result = parse_and_clean(_make_csv(SAMPLE_ROWS), "sales.csv")
        schema = result["detected_schema"]
        assert schema["Date"] == "date"
        assert schema["Total Revenue"] == "numeric"
        assert schema["Region"] == "category"

    def test_whitespace_stripped(self):
        result = parse_and_clean(_make_csv(SAMPLE_ROWS), "sales.csv")
        # "  Widget A  " should be stripped
        first_product = result["sample_rows"][0]["Product Name"]
        assert first_product == "Widget A"

    def test_indian_number_format(self):
        result = parse_and_clean(_make_csv(SAMPLE_ROWS), "sales.csv")
        # "1,200" should parse to numeric 1200.0
        unit_prices = [r["Unit Price"] for r in result["sample_rows"] if r.get("Unit Price")]
        assert all(isinstance(p, (int, float)) for p in unit_prices)

    def test_sample_rows_limit(self):
        result = parse_and_clean(_make_csv(SAMPLE_ROWS), "sales.csv")
        assert len(result["sample_rows"]) <= 5

    def test_null_summary_present(self):
        result = parse_and_clean(_make_csv(SAMPLE_ROWS), "sales.csv")
        # Region and Date have nulls in row 4
        assert "null_summary" in result


class TestXLSXParsing:
    def test_xlsx_parses(self):
        result = parse_and_clean(_make_xlsx(SAMPLE_ROWS), "sales.xlsx")
        assert result["row_count"] == 5
        assert result["column_count"] == 7

    def test_response_is_json_serialisable(self):
        result = parse_and_clean(_make_xlsx(SAMPLE_ROWS), "sales.xlsx")
        # Should not raise
        json.dumps(result)


class TestEdgeCases:
    def test_unsupported_extension_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            parse_and_clean(b"data", "report.pdf")
        assert exc.value.status_code == 415

    def test_empty_file_raises(self):
        from fastapi import HTTPException
        empty_csv = b"Col1,Col2\n"   # headers only, no data rows
        with pytest.raises(HTTPException) as exc:
            parse_and_clean(empty_csv, "empty.csv")
        assert exc.value.status_code == 422
