class ModelNotFoundError(ValueError):
    """Raised when an explicit model is not owned by a registered provider."""


class AllProvidersFailedError(RuntimeError):
    """Raised after every eligible provider has been attempted."""

    def __init__(self, failures: dict[str, Exception]):
        self.failures = failures
        summary = "; ".join(f"{provider}: {error}" for provider, error in failures.items())
        super().__init__(f"All eligible providers failed. {summary}")
