"""Accept CSV/Excel, store under S3 uploads/{user_id}/, enqueue EC2 worker job."""

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import Response

from services.s3 import get_transactions_sample

router = APIRouter()


@router.get("/transactions-sample")
def transactions_sample() -> Response:
    try:
        body, source = get_transactions_sample()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=body,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="transactions_sample.csv"',
            "X-Sample-Source": source,
        },
    )


@router.post("")
def create_upload(file: UploadFile | None = None) -> dict[str, str]:
    # TODO: auth required; validate content-type; put_object S3; put Analyses item; SQS send
    _ = file
    return {"status": "not_implemented"}
