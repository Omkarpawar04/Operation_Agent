from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import current_principal, enforce_rate_limit, get_progression_reader
from app.application.use_cases.queries import GetProgression
from app.ports.services import Principal

router = APIRouter()


@router.get("/progression", dependencies=[Depends(enforce_rate_limit("student-read"))])
def progression(
    principal: Principal = Depends(current_principal),
    use_case: GetProgression = Depends(get_progression_reader),
    course_id: UUID | None = None,
) -> dict[str, list[dict[str, str]]]:
    stages = use_case.execute(principal.user_id, course_id)
    return {"stages": [{"stage": item.stage.value, "status": item.status} for item in stages]}
