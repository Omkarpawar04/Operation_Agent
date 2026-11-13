from fastapi import APIRouter, Depends

from app.api.dependencies import (
    current_principal,
    enforce_rate_limit,
    get_current_user,
    get_delete_student_transcripts,
)
from app.application.use_cases.queries import GetCurrentUser
from app.application.use_cases.transcripts import DeleteStudentTranscripts
from app.ports.services import Principal

router = APIRouter()


@router.get("/me", dependencies=[Depends(enforce_rate_limit("student-read"))])
def me(
    principal: Principal = Depends(current_principal),
    use_case: GetCurrentUser = Depends(get_current_user),
) -> dict[str, str]:
    user_id, role = use_case.execute(principal.user_id)
    return {"id": str(user_id), "role": role}


@router.delete("/me/transcripts")
def delete_transcripts(
    principal: Principal = Depends(current_principal),
    use_case: DeleteStudentTranscripts = Depends(get_delete_student_transcripts),
) -> dict[str, int | str]:
    return {"status": "deleted", "answers_deleted": use_case.execute(principal.user_id)}
