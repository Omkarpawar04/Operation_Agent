from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Course:
    id: UUID
    code: str
    name: str


@dataclass(frozen=True, slots=True)
class Enrollment:
    student_id: UUID
    course_id: UUID
    active: bool = True
