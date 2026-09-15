from fastapi import APIRouter, HTTPException

import scenario_service
from models import ScenarioRequest

router = APIRouter(prefix="/api/scenario", tags=["scenario"])


@router.get("/schema")
def get_schema() -> dict:
    return scenario_service.schema()


@router.post("/infer")
def infer(req: ScenarioRequest) -> dict:
    try:
        return scenario_service.run_scenario(
            current_track_temp_c=req.current_track_temp_c,
            current_ambient_temp_c=req.current_ambient_temp_c,
            forecast_future_ambient_temp_c=req.forecast_future_ambient_temp_c,
            decision_time=req.decision_time,
        )
    except scenario_service.ScenarioInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
