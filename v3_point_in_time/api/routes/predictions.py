from fastapi import APIRouter, HTTPException

import provenance_service
from replay_service import NotFoundError

router = APIRouter(tags=["predictions"])


@router.get("/api/predictions/{prediction_id}")
def get_prediction(prediction_id: str) -> dict:
    try:
        return provenance_service.get_prediction(prediction_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/api/predictions/{prediction_id}/provenance")
def get_prediction_provenance(prediction_id: str) -> dict:
    try:
        return provenance_service.get_provenance(prediction_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/api/predictions/{prediction_id}/explanation")
def get_prediction_explanation(prediction_id: str) -> dict:
    try:
        return provenance_service.get_explanation(prediction_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
