"""
File parsing and data cleaning pipeline for Sales MIS uploads.

Handles .xlsx and .csv files containing typical Indian SME sales data:
Date, Product Name, Region, Salesperson, Quantity, Unit Price, Total Revenue.
"""

import io
import re
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Column name hints used for schema detection
# ---------------------------------------------------------------------------

_DATE_HINTS = {
    "date", "dt", "invoice date", "order date", "sale date",
    "transaction date", "bill date", "created", "created at",
}

_NUMERIC_HINTS = {
    "quantity", "qty", "units", "amount", "revenue", "total",
    "price", "rate", "unit price", "mrp", "value", "sales",
    "discount", "tax", "gst", "profit", "margin", "cost",
}

_CATEGORY_HINTS = {
    "product", "item", "sku", "category", "brand",
    "region", "zone", "state", "city", "area", "territory",
    "salesperson", "rep", "agent", "executive", "manager",
    "channel", "customer", "client", "party",
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_and_clean(file_bytes: bytes, filename: str) -> dict:
    """
    Parse an uploaded file, clean it, infer a schema, and return a
    structured summary dict ready to be sent as JSON.
    """
    df = _load_dataframe(file_bytes, filename)
    df = _clean_dataframe(df)
    schema = _detect_schema(df)
    df = _coerce_types(df, schema)

    return _build_response(df, schema, filename)


# ---------------------------------------------------------------------------
# Step 1 — Load
# ---------------------------------------------------------------------------

def _load_dataframe(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Read bytes into a DataFrame based on file extension."""
    ext = filename.rsplit(".", 1)[-1].lower()

    try:
        if ext == "csv":
            # Try UTF-8 first, fall back to latin-1 (common in Indian exports)
            try:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")

        elif ext in ("xlsx", "xls"):
            df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")

        else:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type '.{ext}'. Upload .csv or .xlsx only.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Could not parse file: {exc}",
        )

    if df.empty:
        raise HTTPException(status_code=422, detail="Uploaded file contains no data.")

    return df


# ---------------------------------------------------------------------------
# Step 2 — Clean
# ---------------------------------------------------------------------------

def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply cleaning steps in order:
    1. Normalise column names
    2. Drop fully empty rows and columns
    3. Remove exact duplicate rows
    4. Strip whitespace from string cells
    5. Fill remaining nulls with sentinels (keeps dtypes stable)
    """
    # Normalise column headers: strip, lower, collapse spaces
    df.columns = [
        re.sub(r"\s+", " ", str(c).strip()).title()
        for c in df.columns
    ]

    # Drop columns that are 100 % empty
    df.dropna(axis=1, how="all", inplace=True)

    # Drop rows that are 100 % empty
    df.dropna(axis=0, how="all", inplace=True)

    # Remove exact duplicate rows
    before = len(df)
    df.drop_duplicates(inplace=True)
    duplicates_removed = before - len(df)

    # Strip whitespace from every string/object cell
    str_cols = df.select_dtypes(include=["object"]).columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip()
        # Restore genuine NaN: cells that were NaN became the string "nan"
        df[col] = df[col].replace({"nan": None, "NaT": None, "": None})

    # Attach cleaning metadata as a DataFrame attribute for later use
    df.attrs["duplicates_removed"] = duplicates_removed
    df.attrs["rows_after_clean"] = len(df)

    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Step 3 — Schema detection
# ---------------------------------------------------------------------------

def _detect_schema(df: pd.DataFrame) -> dict[str, str]:
    """
    Return a mapping of {column_name: detected_type} where detected_type
    is one of: "date", "numeric", "category", "text".

    Strategy:
    - Match column name against hint sets first (fastest, most reliable)
    - Fall back to pandas dtype inference on the column values
    """
    schema: dict[str, str] = {}

    for col in df.columns:
        col_key = col.lower().strip()
        series = df[col].dropna()

        if _matches_hints(col_key, _DATE_HINTS):
            schema[col] = "date"

        elif _matches_hints(col_key, _NUMERIC_HINTS):
            schema[col] = "numeric"

        elif _matches_hints(col_key, _CATEGORY_HINTS):
            schema[col] = "category"

        else:
            # Fallback: inspect actual values
            schema[col] = _infer_from_values(series)

    return schema


def _matches_hints(col_key: str, hints: set[str]) -> bool:
    """True if any hint is a substring of the column name."""
    return any(hint in col_key for hint in hints)


def _infer_from_values(series: pd.Series) -> str:
    """Infer column type from a sample of non-null values."""
    if series.empty:
        return "text"

    # Already numeric dtype
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    # Already datetime dtype
    if pd.api.types.is_datetime64_any_dtype(series):
        return "date"

    # Try coercing a sample to datetime
    sample = series.head(20).astype(str)
    try:
        parsed = pd.to_datetime(sample, infer_datetime_format=True, errors="coerce")
        if parsed.notna().mean() >= 0.7:   # 70 %+ parse rate → treat as date
            return "date"
    except Exception:
        pass

    # Try coercing a sample to numeric
    try:
        numeric_sample = pd.to_numeric(
            sample.str.replace(",", "", regex=False),  # handle "1,23,456" Indian format
            errors="coerce",
        )
        if numeric_sample.notna().mean() >= 0.8:
            return "numeric"
    except Exception:
        pass

    # Low-cardinality string → category; high-cardinality → text
    unique_ratio = series.nunique() / len(series)
    return "category" if unique_ratio < 0.5 else "text"


# ---------------------------------------------------------------------------
# Step 4 — Coerce types
# ---------------------------------------------------------------------------

def _coerce_types(df: pd.DataFrame, schema: dict[str, str]) -> pd.DataFrame:
    """
    Convert each column to its detected type in-place.
    Invalid conversions are set to NaN / NaT rather than raising.
    """
    for col, dtype in schema.items():
        if col not in df.columns:
            continue

        if dtype == "date":
            df[col] = pd.to_datetime(df[col], infer_datetime_format=True, errors="coerce")

        elif dtype == "numeric":
            # Remove commas used in Indian number formatting (e.g. "1,23,456")
            if df[col].dtype == object:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace(",", "", regex=False)
                    .str.replace("₹", "", regex=False)
                    .str.strip()
                )
            df[col] = pd.to_numeric(df[col], errors="coerce")

        elif dtype == "category":
            df[col] = df[col].astype("category")

    return df


# ---------------------------------------------------------------------------
# Step 5 — Build response
# ---------------------------------------------------------------------------

def _build_response(df: pd.DataFrame, schema: dict[str, str], filename: str) -> dict:
    """Serialise the cleaned DataFrame into a structured JSON-safe dict."""

    # Null summary per column
    null_counts: dict[str, int] = df.isnull().sum().to_dict()
    null_summary = {
        col: {"null_count": int(count), "null_pct": round(count / len(df) * 100, 1)}
        for col, count in null_counts.items()
        if count > 0
    }

    # Sample rows (first 5) — convert to JSON-safe types
    sample_df = df.head(5).copy()
    sample_rows = _to_json_safe(sample_df)

    # Column dtype labels
    dtypes = {col: str(df[col].dtype) for col in df.columns}

    return {
        "filename": filename,
        "row_count": len(df),
        "column_count": len(df.columns),
        "duplicates_removed": df.attrs.get("duplicates_removed", 0),
        "columns": list(df.columns),
        "dtypes": dtypes,
        "detected_schema": schema,
        "null_summary": null_summary,
        "sample_rows": sample_rows,
    }


def _to_json_safe(df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Convert a DataFrame to a list of dicts where every value is
    JSON-serialisable (handles NaT, NaN, Timestamp, numpy ints/floats).
    """
    records = []
    for _, row in df.iterrows():
        record: dict[str, Any] = {}
        for col, val in row.items():
            if pd.isna(val) if not isinstance(val, (list, dict)) else False:
                record[col] = None
            elif isinstance(val, pd.Timestamp):
                record[col] = val.isoformat()
            elif isinstance(val, (np.integer,)):
                record[col] = int(val)
            elif isinstance(val, (np.floating,)):
                record[col] = round(float(val), 4)
            elif isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
                record[col] = None
            else:
                record[col] = val
        records.append(record)
    return records
