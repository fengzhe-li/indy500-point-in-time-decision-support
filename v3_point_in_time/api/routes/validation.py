from fastapi import APIRouter

import query_service
from models import ValidationSummaryResponse

router = APIRouter(tags=["validation"])


@router.get("/api/validation/summary", response_model=ValidationSummaryResponse)
def validation_summary() -> ValidationSummaryResponse:
    return ValidationSummaryResponse(**query_service.validation_summary())
