"""
POST /api/v1/upload

Accepts a multipart/form-data file upload (.csv or .xlsx),
runs it through the parsing/cleaning pipeline, and returns
a structured JSON summary of the dataset.
"""

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.file_parser import parse_and_clean
from app.services.column_detector import detect_columns, clean_header_rows

router = APIRouter(prefix="/upload", tags=["Upload"])

# Max file size: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_TYPES = {
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "application/octet-stream",   # some browsers send this for .xlsx
}


@router.post("", summary="Upload a sales data file (CSV or XLSX)")
async def upload_file(
    file: UploadFile = File(..., description="Sales data file (.csv or .xlsx)"),
    db: Session = Depends(get_db),
):
    """
    Upload a sales data file and receive a cleaned, structured JSON summary.

    Returns:
    - **filename**: original filename
    - **row_count**: rows after cleaning
    - **column_count**: number of columns detected
    - **duplicates_removed**: number of duplicate rows dropped
    - **columns**: list of column names (normalised)
    - **dtypes**: pandas dtype for each column after coercion
    - **detected_schema**: inferred type per column (date/numeric/category/text)
    - **null_summary**: columns that have nulls, with count and percentage
    - **sample_rows**: first 5 rows as JSON objects
    """

    # --- Validation ---

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "xlsx", "xls"):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '.{ext}'. Please upload a .csv or .xlsx file.",
        )

    # Read all bytes (enforces size limit)
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(file_bytes) // 1024} KB). Max allowed: 10 MB.",
        )

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # --- Parse & clean ---
    result = parse_and_clean(file_bytes, file.filename)

    # --- Column role detection ---
    # Re-build a lightweight DataFrame from the parsed sample to run detection.
    # We use the full file bytes again so the detector sees all rows for
    # cardinality checks, not just the 5-row sample.
    import io, pandas as pd
    try:
        ext_lower = file.filename.rsplit(".", 1)[-1].lower()
        if ext_lower == "csv":
            try:
                df_full = pd.read_csv(io.BytesIO(file_bytes), encoding="utf-8")
            except UnicodeDecodeError:
                df_full = pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")
        else:
            df_full = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")

        df_full = clean_header_rows(df_full)
        result["column_roles"] = detect_columns(df_full)
    except Exception:
        result["column_roles"] = None   # graceful degradation — never block upload

    return result
