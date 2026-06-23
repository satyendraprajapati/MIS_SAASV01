"""
Column Auto-Detection Module for Sales BI SaaS.

Intelligently identifies the semantic role of each column in a sales DataFrame
without any manual mapping. Designed for messy, real-world Indian SME Excel
files that may have:
  - Hindi/mixed-language column names
  - Merged headers (extra junk rows at the top)
  - Inconsistent casing, spacing, special characters
  - Numeric data stored as strings with commas / ₹ symbols

Public API
----------
    detect_columns(df)         -> DetectionResult dict
    clean_header_rows(df)      -> DataFrame with junk top-rows stripped
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Constants — keyword hint tables
# ---------------------------------------------------------------------------

# Each role maps to a tuple of (keywords, weight).
# Weights let us rank ambiguous matches (e.g. "Total Sales Amount" could be
# revenue or quantity — revenue hints carry higher weight).

_ROLE_HINTS: dict[str, list[tuple[list[str], float]]] = {
    "date": [
        (["date", "dt", "dated", "invoice date", "order date", "sale date",
          "transaction date", "bill date", "billing date", "voucher date",
          "created", "created at", "period", "month", "year", "week",
          # Hindi transliterations
          "tarikh", "tithi"], 1.0),
    ],
    "revenue": [
        (["total revenue", "total sales", "net revenue", "gross revenue",
          "total amount", "net amount", "gross amount", "invoice amount",
          "bill amount", "total value", "sale value", "net value"], 1.0),
        (["revenue", "sales", "amount", "value", "total", "turnover",
          "income", "earning", "receipt",
          # Hindi transliterations
          "rakam", "raashi", "bikri"], 0.8),
        (["price", "rate", "mrp", "sp", "selling price"], 0.5),
    ],
    "quantity": [
        (["total qty", "total quantity", "total units", "units sold",
          "pieces sold", "pcs sold"], 1.0),
        (["quantity", "qty", "units", "pieces", "pcs", "count", "nos",
          "number", "volume",
          # Hindi transliterations
          "matra", "sankhya"], 0.9),
    ],
    "product": [
        (["product name", "item name", "article name", "goods name",
          "material name", "product description"], 1.0),
        (["product", "item", "article", "goods", "material", "sku",
          "part no", "part number", "description", "particulars",
          # Hindi transliterations
          "vasthu", "cheez", "maal"], 0.8),
    ],
    "region": [
        (["sales region", "sales zone", "sales territory", "sales area",
          "branch location", "office location"], 1.0),
        (["region", "zone", "territory", "area", "location", "city",
          "state", "district", "branch", "market",
          # Hindi transliterations
          "kshetra", "pradesh", "sheher"], 0.9),
    ],
    "salesperson": [
        (["sales representative", "sales rep", "sales executive",
          "sales officer", "account manager", "field executive",
          "business development executive", "bde"], 1.0),
        (["salesperson", "agent", "employee", "staff", "person",
          "rep name", "executive name", "user name",
          # Hindi transliterations
          "vikreta", "karmchari"], 0.9),
        # "name" alone is very ambiguous — low weight
        (["name"], 0.3),
    ],
}

# Max unique values to still qualify as low / medium cardinality
_CARDINALITY_LOW = 30       # region, salesperson
_CARDINALITY_MEDIUM = 200   # product

# Minimum fraction of non-null values needed to consider a column
_MIN_COVERAGE = 0.5

# Minimum confidence to accept a detection (below this → None)
_MIN_CONFIDENCE = 0.25


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ColumnMatch:
    column: Optional[str]
    confidence: float               # 0.0 – 1.0
    reason: str                     # human-readable explanation

    def to_dict(self) -> dict:
        return {
            "column": self.column,
            "confidence": round(self.confidence, 3),
            "reason": self.reason,
        }


@dataclass
class DetectionResult:
    date: ColumnMatch = field(default_factory=lambda: ColumnMatch(None, 0.0, "not detected"))
    revenue: ColumnMatch = field(default_factory=lambda: ColumnMatch(None, 0.0, "not detected"))
    quantity: ColumnMatch = field(default_factory=lambda: ColumnMatch(None, 0.0, "not detected"))
    product: ColumnMatch = field(default_factory=lambda: ColumnMatch(None, 0.0, "not detected"))
    region: ColumnMatch = field(default_factory=lambda: ColumnMatch(None, 0.0, "not detected"))
    salesperson: ColumnMatch = field(default_factory=lambda: ColumnMatch(None, 0.0, "not detected"))
    undetected: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        assigned = set()
        out: dict = {}
        for role in ("date", "revenue", "quantity", "product", "region", "salesperson"):
            match: ColumnMatch = getattr(self, role)
            out[role] = match.to_dict()
            if match.column:
                assigned.add(match.column)
        out["undetected"] = self.undetected
        return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_columns(df: pd.DataFrame) -> dict:
    """
    Identify the semantic role of each column in a sales DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Raw or lightly cleaned sales data. Column names may be messy.

    Returns
    -------
    dict with keys: date, revenue, quantity, product, region, salesperson,
                    undetected
    Each role value is:
        { "column": str | None, "confidence": float, "reason": str }
    """
    if df.empty or len(df.columns) == 0:
        return DetectionResult().to_dict()

    # Pre-process: normalise column names for matching (keep originals for output)
    norm_map = {col: _normalise(col) for col in df.columns}

    result = DetectionResult()
    assigned: set[str] = set()          # track columns already claimed by a role

    # Score every column against every role, then greedily assign best match
    # per role (highest confidence first so high-priority roles grab first).
    scores: dict[str, dict[str, tuple[float, str]]] = {
        role: {} for role in ("date", "revenue", "quantity", "product", "region", "salesperson")
    }

    for col in df.columns:
        norm = norm_map[col]
        series = df[col].dropna()

        for role in scores:
            conf, reason = _score_column(col, norm, series, role)
            if conf > 0:
                scores[role][col] = (conf, reason)

    # Assign: process roles in priority order; each column can only be claimed once
    for role in ("date", "revenue", "quantity", "product", "region", "salesperson"):
        best_col, best_conf, best_reason = None, 0.0, "no match"

        for col, (conf, reason) in scores[role].items():
            if col in assigned:
                continue
            if conf > best_conf:
                best_col, best_conf, best_reason = col, conf, reason

        if best_col and best_conf >= _MIN_CONFIDENCE:
            match = ColumnMatch(best_col, best_conf, best_reason)
            assigned.add(best_col)
        else:
            match = ColumnMatch(None, 0.0, "not detected")

        setattr(result, role, match)

    # Undetected = all columns not claimed
    result.undetected = [c for c in df.columns if c not in assigned]

    return result.to_dict()


def clean_header_rows(df: pd.DataFrame, max_scan: int = 5) -> pd.DataFrame:
    """
    Remove junk rows at the top of the DataFrame that look like merged
    Excel headers or metadata (e.g. company name, report title, blank rows).

    Strategy: scan the first `max_scan` rows; the real header row is the first
    row where >= 50 % of cells are non-null non-numeric strings.  Everything
    above it is dropped and that row becomes the new header.

    Parameters
    ----------
    df       : Raw DataFrame (pandas reads merged headers into row 0,1,2…)
    max_scan : How many rows to inspect (default 5)
    """
    for i in range(min(max_scan, len(df))):
        row = df.iloc[i]
        non_null = row.dropna()
        if len(non_null) == 0:
            continue
        str_like = non_null.apply(lambda v: isinstance(v, str) and not _looks_numeric(str(v)))
        if str_like.mean() >= 0.5:
            # This looks like a header row
            new_df = df.iloc[i + 1:].copy()
            new_df.columns = [str(v).strip() for v in df.iloc[i].values]
            new_df = new_df.reset_index(drop=True)
            # Drop any all-null rows that may remain
            new_df.dropna(how="all", inplace=True)
            return new_df.reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Scoring engine — the core of the module
# ---------------------------------------------------------------------------

def _score_column(
    col: str,
    norm: str,
    series: pd.Series,
    role: str,
) -> tuple[float, str]:
    """
    Return (confidence 0-1, reason_string) for assigning `col` to `role`.

    Scoring is additive across evidence signals, then clipped to [0, 1].
    """
    if series.empty or len(series) / max(len(series), 1) < _MIN_COVERAGE:
        return 0.0, "insufficient data"

    score = 0.0
    reasons: list[str] = []

    # ── 1. Name-hint score ──────────────────────────────────────────────────
    hint_score, hint_reason = _name_hint_score(norm, role)
    score += hint_score
    if hint_reason:
        reasons.append(hint_reason)

    # ── 2. Value-based evidence ─────────────────────────────────────────────
    val_score, val_reason = _value_evidence(series, role)
    score += val_score
    if val_reason:
        reasons.append(val_reason)

    # ── 3. Cardinality checks (for categorical roles) ────────────────────────
    card_score, card_reason = _cardinality_check(series, role)
    score += card_score
    if card_reason:
        reasons.append(card_reason)

    # Clip final score
    score = min(score, 1.0)
    return score, "; ".join(reasons) if reasons else "no signal"


def _name_hint_score(norm: str, role: str) -> tuple[float, str]:
    """Score based on keyword matches in the normalised column name."""
    best_score = 0.0
    best_kw = ""

    for keywords, weight in _ROLE_HINTS[role]:
        for kw in keywords:
            # Exact substring match
            if kw in norm:
                # Longer keyword = more specific = higher score
                specificity = min(len(kw) / 20, 1.0)
                candidate = weight * (0.6 + 0.4 * specificity)
                if candidate > best_score:
                    best_score = candidate
                    best_kw = kw

    if best_score > 0:
        return best_score, f"name hint '{best_kw}'"
    return 0.0, ""


def _value_evidence(series: pd.Series, role: str) -> tuple[float, str]:
    """Score based on what the actual cell values look like."""

    if role == "date":
        return _evidence_date(series)
    elif role == "revenue":
        return _evidence_revenue(series)
    elif role == "quantity":
        return _evidence_quantity(series)
    elif role in ("product", "region", "salesperson"):
        return _evidence_categorical(series)
    return 0.0, ""


def _evidence_date(series: pd.Series) -> tuple[float, str]:
    """Detect date-like values."""
    # Already datetime dtype
    if pd.api.types.is_datetime64_any_dtype(series):
        return 0.4, "datetime dtype"

    # Try parsing a sample as dates
    sample = series.head(30).astype(str)
    try:
        parsed = pd.to_datetime(sample, infer_datetime_format=True, errors="coerce")
        rate = parsed.notna().mean()
        if rate >= 0.8:
            return 0.4, f"date parse rate {rate:.0%}"
        elif rate >= 0.5:
            return 0.2, f"partial date parse rate {rate:.0%}"
    except Exception:
        pass
    return 0.0, ""


def _evidence_revenue(series: pd.Series) -> tuple[float, str]:
    """Detect revenue-like numeric columns."""
    numeric = _try_numeric(series)
    if numeric is None:
        return 0.0, ""

    rate = numeric.notna().mean()
    if rate < 0.5:
        return 0.0, ""

    vals = numeric.dropna()
    # Revenue is typically large and has decimals
    median_val = vals.median()
    has_decimals = (vals % 1 != 0).mean() > 0.1

    if median_val > 100:
        score = 0.3
        reason = f"numeric, median={median_val:.0f}"
        if has_decimals:
            score += 0.05
            reason += ", has decimals"
        return score, reason
    return 0.1, "numeric but small values"


def _evidence_quantity(series: pd.Series) -> tuple[float, str]:
    """Detect quantity-like integer columns."""
    numeric = _try_numeric(series)
    if numeric is None:
        return 0.0, ""

    vals = numeric.dropna()
    if vals.empty:
        return 0.0, ""

    # Quantities are usually small positive integers
    all_integers = (vals % 1 == 0).mean() > 0.9
    median_val = vals.median()
    positive = (vals > 0).mean() > 0.9

    if all_integers and positive and median_val < 10_000:
        return 0.3, f"integer-like, median={median_val:.0f}"
    elif all_integers:
        return 0.15, "integer-like"
    return 0.0, ""


def _evidence_categorical(series: pd.Series) -> tuple[float, str]:
    """Detect string/categorical columns."""
    if pd.api.types.is_numeric_dtype(series):
        return 0.0, ""
    if pd.api.types.is_datetime64_any_dtype(series):
        return 0.0, ""

    str_series = series.astype(str)
    avg_len = str_series.str.len().mean()

    # Strings that look like numbers are not categorical
    numeric_rate = str_series.apply(_looks_numeric).mean()
    if numeric_rate > 0.5:
        return 0.0, ""

    if avg_len > 0:
        return 0.2, f"string, avg_len={avg_len:.1f}"
    return 0.0, ""


def _cardinality_check(series: pd.Series, role: str) -> tuple[float, str]:
    """Reward or penalise based on unique value count for categorical roles."""
    if role not in ("product", "region", "salesperson"):
        return 0.0, ""

    n_unique = series.nunique()
    n_total = len(series)

    if role == "region":
        if n_unique <= _CARDINALITY_LOW:
            return 0.15, f"low cardinality ({n_unique} unique)"
        elif n_unique <= 60:
            return 0.05, f"medium cardinality ({n_unique} unique)"
        else:
            return -0.2, f"too many unique values for region ({n_unique})"

    elif role == "salesperson":
        if n_unique <= _CARDINALITY_LOW:
            return 0.1, f"low cardinality ({n_unique} unique)"
        elif n_unique <= 100:
            return 0.0, ""
        else:
            return -0.1, f"high cardinality ({n_unique})"

    elif role == "product":
        ratio = n_unique / max(n_total, 1)
        if ratio < 0.8:
            return 0.1, f"medium cardinality ({n_unique}/{n_total})"
        else:
            return -0.05, f"high cardinality ratio ({ratio:.1%})"

    return 0.0, ""


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _normalise(col_name: str) -> str:
    """
    Normalise a column name for keyword matching:
    - Strip Unicode accents / diacritics
    - Lowercase
    - Replace non-alphanumeric runs with single space
    - Strip leading/trailing whitespace

    This handles column names like:
      "Invoice Date " → "invoice date"
      "TOTAL_REVENUE"  → "total revenue"
      "Qty."           → "qty"
      "बिक्री"  (Hindi) → kept as-is after NFKD normalisation
    """
    # NFKD normalisation handles accented chars; encode/decode strips them
    text = unicodedata.normalize("NFKD", str(col_name))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return text


def _try_numeric(series: pd.Series) -> Optional[pd.Series]:
    """
    Try to convert series to numeric, handling Indian formatting like
    "1,23,456" and "₹ 5,000.00".
    Returns None if conversion rate is below 50 %.
    """
    if pd.api.types.is_numeric_dtype(series):
        return series

    cleaned = (
        series.astype(str)
        .str.replace("₹", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    numeric = pd.to_numeric(cleaned, errors="coerce")
    if numeric.notna().mean() >= 0.5:
        return numeric
    return None


def _looks_numeric(val: str) -> bool:
    """True if a string value looks like a number (with optional ₹ / commas)."""
    cleaned = val.replace("₹", "").replace(",", "").strip()
    try:
        float(cleaned)
        return True
    except ValueError:
        return False
