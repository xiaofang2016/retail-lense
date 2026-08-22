"""Accept CSV/Excel, store under S3 uploads/{user_id}/, enqueue EC2 worker job."""

from fastapi import APIRouter, UploadFile

router = APIRouter()


@router.post("")
def create_upload(file: UploadFile | None = None) -> dict[str, str]:
    # TODO: auth required; validate content-type; put_object S3; put Analyses item; SQS send
    _ = file
    return {"status": "not_implemented"}
