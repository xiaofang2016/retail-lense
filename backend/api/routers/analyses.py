"""Analysis job creation, status polling, listing, and the public UCI reference report."""

from datetime import UTC, datetime
from uuid import uuid4

from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_current_user
from core.settings import get_settings
from schema.analysis import (
    AnalysisCreateIn,
    AnalysisCreateOut,
    AnalysisListOut,
    AnalysisStatusOut,
    AnalysisSummaryOut,
)
from schema.user import UserRecord
from services import s3
from services.analysis_store import get_analysis_store
from shared.models import AnalysisItem

router = APIRouter()

_CONTENT_TYPES = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@router.get("/reference")
def reference_analysis() -> dict[str, str]:
    # TODO: read precomputed public results from S3 public/ prefix
    return {"status": "not_implemented"}


@router.post("", response_model=AnalysisCreateOut)
def create_analysis(
    body: AnalysisCreateIn,
    current_user: UserRecord = Depends(get_current_user),
) -> AnalysisCreateOut:
    settings = get_settings()
    analysis_id = str(uuid4())
    key = s3.upload_key(current_user.user_id, analysis_id, body.file_extension)
    upload_url = s3.presign_put_url(key, _CONTENT_TYPES[body.file_extension])

    item: AnalysisItem = {
        "analysis_id": analysis_id,
        "user_id": current_user.user_id,
        "status": "pending",
        "k": settings.analysis_k,
        "s3_upload_key": key,
        "s3_result_key": "",
        "error_message": None,
        "created_at": datetime.now(UTC).isoformat(),
        "original_filename": body.file_name,
    }
    get_analysis_store().create(item)

    return AnalysisCreateOut(analysis_id=analysis_id, upload_url=upload_url)


@router.get("/{analysis_id}/status", response_model=AnalysisStatusOut)
def get_analysis_status(
    analysis_id: str,
    current_user: UserRecord = Depends(get_current_user),
) -> AnalysisStatusOut:
    item = get_analysis_store().get(analysis_id)
    if item is None or item["user_id"] != current_user.user_id:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return AnalysisStatusOut(
        analysis_id=item["analysis_id"],
        status=item["status"],
        s3_result_key=item.get("s3_result_key") or None,
        error_message=item.get("error_message"),
    )


@router.get("", response_model=AnalysisListOut)
def list_analyses(current_user: UserRecord = Depends(get_current_user)) -> AnalysisListOut:
    items = get_analysis_store().list_by_user(current_user.user_id)
    return AnalysisListOut(
        items=[
            AnalysisSummaryOut(
                analysis_id=item["analysis_id"],
                status=item["status"],
                s3_upload_key=item["s3_upload_key"],
                s3_result_key=item.get("s3_result_key") or None,
                error_message=item.get("error_message"),
                created_at=item["created_at"],
                original_filename=item["original_filename"],
            )
            for item in items
        ]
    )


@router.get("/{analysis_id}/report")
def get_analysis_report(
    analysis_id: str,
    current_user: UserRecord = Depends(get_current_user),
) -> dict:
    item = get_analysis_store().get(analysis_id)
    if item is None or item["user_id"] != current_user.user_id:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if item["status"] != "done" or not item.get("s3_result_key"):
        raise HTTPException(status_code=409, detail="Report is not ready yet")

    try:
        return s3.get_object_json(item["s3_result_key"])
    except ClientError as exc:
        # The Analyses item says done, but the S3 object isn't reachable (not yet written,
        # or removed) -- surface this as a clean 502 instead of an unhandled 500.
        raise HTTPException(status_code=502, detail="Report file could not be read from storage") from exc


@router.get("/{analysis_id}")
def get_analysis(
    analysis_id: str,
    current_user: UserRecord = Depends(get_current_user),
) -> AnalysisSummaryOut:
    item = get_analysis_store().get(analysis_id)
    if item is None or item["user_id"] != current_user.user_id:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return AnalysisSummaryOut(
        analysis_id=item["analysis_id"],
        status=item["status"],
        s3_upload_key=item["s3_upload_key"],
        s3_result_key=item.get("s3_result_key") or None,
        error_message=item.get("error_message"),
        created_at=item["created_at"],
        original_filename=item["original_filename"],
    )
