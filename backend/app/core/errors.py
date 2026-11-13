class ApplicationError(Exception):
    code = "application_error"
    status_code = 400

    def __init__(self, message: str = "Request could not be completed") -> None:
        super().__init__(message)


class NotFound(ApplicationError):
    code = "not_found"
    status_code = 404


class Conflict(ApplicationError):
    code = "conflict"
    status_code = 409


class StageLocked(Conflict):
    code = "stage_locked"


class RetakeLimitReached(Conflict):
    code = "retake_policy_restriction"


class AssessmentNotReady(Conflict):
    code = "assessment_not_ready"


class EnrollmentRequired(ApplicationError):
    code = "enrollment_required"
    status_code = 403


class Forbidden(ApplicationError):
    code = "forbidden"
    status_code = 403


class Unavailable(ApplicationError):
    code = "dependency_unavailable"
    status_code = 503


class ProviderUnavailable(Unavailable):
    code = "interview_provider_unavailable"


class ProviderOutputRejected(ApplicationError):
    code = "provider_output_rejected"
    status_code = 502

    def __init__(self, message: str, category: str = "invalid_output") -> None:
        super().__init__(message)
        self.category = category
