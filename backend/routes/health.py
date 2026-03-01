from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "Cleannest AI Receptionist Backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
