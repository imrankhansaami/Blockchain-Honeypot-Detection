"""Domain exceptions with stable error codes for the API layer."""

from __future__ import annotations


class AppError(Exception):
    """Base class for expected application errors."""

    status_code = 400
    code = "app_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class UnsupportedChainError(AppError):
    status_code = 400
    code = "unsupported_chain"


class RpcUnavailableError(AppError):
    status_code = 503
    code = "rpc_unavailable"


class SSRFBlockedError(AppError):
    status_code = 400
    code = "rpc_endpoint_blocked"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class SimulationError(AppError):
    status_code = 502
    code = "simulation_error"


class AnalysisError(AppError):
    status_code = 500
    code = "analysis_error"
