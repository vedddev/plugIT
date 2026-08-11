class SmartLLMError(Exception):
    """Base class for safe, client-facing SmartLLM failures."""

    status_code = 500
    error_type = "server_error"
    code = "internal_error"
    param = None

    def __init__(self, message: str | None = None, *, provider: str | None = None, model: str | None = None):
        super().__init__(message or self.__class__.__name__)
        self.message = message or self.__class__.__name__
        self.provider, self.model = provider, model


class InvalidModelError(SmartLLMError):
    status_code, error_type, code, param = 404, "invalid_request_error", "model_not_found", "model"


class ProviderNotFoundError(SmartLLMError):
    status_code, code = 503, "provider_not_found"


class ProviderUnavailableError(SmartLLMError):
    status_code, code = 503, "provider_unavailable"


class ProviderAPIError(SmartLLMError):
    status_code, code = 502, "provider_error"


class AllProvidersFailedError(SmartLLMError):
    status_code, code = 503, "all_providers_failed"

    def __init__(self, failures: dict[str, Exception]):
        self.failures = failures
        super().__init__("All available LLM providers failed.")


class RateLimitError(SmartLLMError):
    status_code, error_type, code = 429, "rate_limit_error", "rate_limit_exceeded"


class QuotaExceededError(SmartLLMError):
    status_code, error_type, code = 429, "insufficient_quota", "quota_exceeded"


class AuthenticationError(SmartLLMError):
    status_code, error_type, code = 401, "authentication_error", "invalid_api_key"


class ValidationError(SmartLLMError):
    status_code, error_type, code = 422, "invalid_request_error", "invalid_request"


class CacheError(SmartLLMError):
    status_code, code = 500, "cache_error"
