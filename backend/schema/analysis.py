from typing import Literal

from pydantic import BaseModel


class AnalysisCreateIn(BaseModel):
    """Client tells us the file type up front so we can presign the exact upload key."""

    file_extension: Literal["csv", "xlsx"]
    # Original client-side filename (e.g. "august_transactions.csv"), kept only for display
    # in the Analysis Library -- the S3 object itself is always stored as raw.<extension>.
    file_name: str
    file_size_bytes: int


class AnalysisCreateOut(BaseModel):
    analysis_id: str
    upload_url: str


class AnalysisStatusOut(BaseModel):
    analysis_id: str
    status: str
    s3_result_key: str | None = None
    error_message: str | None = None


class AnalysisSummaryOut(BaseModel):
    """One row in the Analysis Library list."""

    analysis_id: str
    status: str
    s3_upload_key: str
    s3_result_key: str | None = None
    error_message: str | None = None
    created_at: str
    original_filename: str


class AnalysisListOut(BaseModel):
    items: list[AnalysisSummaryOut]
