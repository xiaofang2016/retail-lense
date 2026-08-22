"""Analysis job status and the public UCI reference report."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/reference")
def reference_analysis() -> dict[str, str]:
    # TODO: read precomputed public results from S3 public/ prefix
    return {"status": "not_implemented"}


@router.get("/{analysis_id}")
def get_analysis(analysis_id: str) -> dict[str, str]:
    # TODO: get Analyses item from DynamoDB; enforce owner
    return {"analysis_id": analysis_id, "status": "not_implemented"}
