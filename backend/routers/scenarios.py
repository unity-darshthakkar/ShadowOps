import json
import pathlib
from fastapi import APIRouter, HTTPException
from backend.models.schemas import ScenarioMeta

router = APIRouter()

_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"


def load_scenarios() -> list[dict]:
    path = _DATA_DIR / "seed_scenarios.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # Support both a single scenario dict and a list
    if isinstance(data, list):
        return data
    return [data]


@router.get("/scenarios", response_model=list[ScenarioMeta])
def list_scenarios() -> list[ScenarioMeta]:
    scenarios = load_scenarios()
    result = []
    for s in scenarios:
        events = s.get("events", [])
        ticket_ids = {ev["ticket_id"] for ev in events}
        result.append(
            ScenarioMeta(
                scenario_id=s["scenario_id"],
                name=s["name"],
                description=s["description"],
                event_count=len(events),
                ticket_count=len(ticket_ids),
            )
        )
    return result


def get_scenario_by_id(scenario_id: str) -> dict:
    for s in load_scenarios():
        if s["scenario_id"] == scenario_id:
            return s
    raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")
