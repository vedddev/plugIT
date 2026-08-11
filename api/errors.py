import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from errors.exceptions import SmartLLMError

logger = logging.getLogger(__name__)


def error_body(message: str, error_type: str, code: str, param=None) -> dict:
    return {"error": {"message": message, "type": error_type, "param": param, "code": code}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(SmartLLMError)
    async def smartllm_error_handler(_: Request, exc: SmartLLMError):
        return JSONResponse(
            content=error_body(exc.message, exc.error_type, exc.code, exc.param),
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        param = ".".join(str(part) for part in first.get("loc", [])[1:]) or None
        status_code = 400 if first.get("type") == "json_invalid" else 422
        return JSONResponse(
            content=error_body("Invalid request body.", "invalid_request_error", "invalid_request", param),
            status_code=status_code,
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(_: Request, exc: Exception):
        logger.exception("Unhandled SmartLLM request error: %s", type(exc).__name__)
        return JSONResponse(
            content=error_body("An internal server error occurred.", "server_error", "internal_error"),
            status_code=500,
        )
