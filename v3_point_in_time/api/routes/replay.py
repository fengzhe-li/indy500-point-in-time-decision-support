from typing import List

from fastapi import APIRouter, HTTPException

import replay_service
from replay_service import NotFoundError
from models import ReplayCaseSummary

router = APIRouter(tags=["replay"])


@router.get("/api/replay/cases", response_model=List[ReplayCaseSummary])
def list_cases() -> List[ReplayCaseSummary]:
    return [ReplayCaseSummary(**c) for c in replay_service.list_cases()]


@router.get("/api/replay/cases/representative")
def get_representative_case() -> dict:
    try:
        return replay_service.select_representative_case()
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/api/replay/cases/{case_id}", response_model=ReplayCaseSummary)
def get_case(case_id: str) -> ReplayCaseSummary:
    try:
        return ReplayCaseSummary(**replay_service.get_case(case_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/api/replay/cases/{case_id}/events")
def get_case_events(case_id: str) -> List[dict]:
    try:
        return replay_service.get_case_events(case_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/api/replay/cases/{case_id}/outlook")
def get_case_outlook(case_id: str) -> dict:
    try:
        return replay_service.get_case_outlook(case_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/api/replay/cases/{case_id}/scoring")
def get_case_scoring(case_id: str) -> dict:
    try:
        return replay_service.get_case_scoring(case_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/api/replay/abstentions")
def get_abstentions() -> List[dict]:
    return replay_service.load_abstention_summary()
