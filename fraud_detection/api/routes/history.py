from fastapi import APIRouter, Depends
from typing import Optional
from fraud_detection.api.dependencies import get_services, verify_token

router = APIRouter()

@router.get("/history")
async def get_history(
    limit: int = 100,
    offset: int = 0,
    decision: Optional[str] = None,
    user=Depends(verify_token)
):
    """
    Fetch transaction history with pagination and optional decision filter.
    Returns both the paginated records and the total count (unfiltered by pagination).
    """
    svc = get_services()

    # Get paginated records
    records = svc.storage_service.get_transactions(limit, offset, decision)

    # Get the true total count (ignoring pagination)
    total = svc.storage_service.count_transactions(decision)

    return {
        "records": records,
        "total": total,
        "limit": limit,
        "offset": offset
    }
