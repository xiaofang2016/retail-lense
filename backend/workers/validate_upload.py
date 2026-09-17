"""Schema-check an uploaded CSV/Excel file. Header-only read: csv module for CSV, openpyxl for XLSX.

Called from workers/clustering.py as a step in the single consolidated worker, not run standalone.
"""

from __future__ import annotations

import csv
import io

import openpyxl

from shared.schema import validate_columns


def _csv_header(body: bytes) -> list[str]:
    text = body.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    return next(reader, [])


def _xlsx_header(body: bytes) -> list[str]:
    workbook = openpyxl.load_workbook(io.BytesIO(body), read_only=True, data_only=True)
    sheet = workbook.active
    row = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
    return [str(cell) for cell in row if cell is not None]


def validate(body: bytes, filename: str) -> None:
    """Raise ValueError with a user-facing message if required columns are missing."""
    if filename.lower().endswith(".xlsx"):
        header = _xlsx_header(body)
    else:
        header = _csv_header(body)
    validate_columns(header)
