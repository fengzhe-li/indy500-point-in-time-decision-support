from fastapi import APIRouter, Response

import health_service
import query_service
from models import SystemStatusResponse

router = APIRouter(tags=["system"])


@router.get("/api/system/status", response_model=SystemStatusResponse)
def system_status() -> SystemStatusResponse:
    return SystemStatusResponse(**query_service.system_status())


@router.get("/api/system/readiness")
def readiness(response: Response) -> dict:
    result = health_service.readiness()
    response.status_code = 200 if result["status"] == "READY" else 503
    return result
