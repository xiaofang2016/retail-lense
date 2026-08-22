"""Private report listing and CSV export for the owning account."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_reports() -> dict[str, list]:
    # TODO: query Analyses by user_id
    return {"items": []}


@router.get("/{analysis_id}/export")
def export_report(analysis_id: str) -> dict[str, str]:
    # TODO: presign or stream S3 results/{user_id}/{analysis_id}.csv
    return {"analysis_id": analysis_id, "status": "not_implemented"}
