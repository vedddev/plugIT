import time
from enum import Enum


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 60,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.failure_count = 0
        self.last_failure_time = None

        self.state = CircuitState.CLOSED

    def allow_request(self) -> bool:
        """
        Can we call this provider?
        """

        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:

            elapsed = time.time() - self.last_failure_time

            if elapsed >= self.recovery_timeout:

                print("[Circuit] HALF OPEN")

                self.state = CircuitState.HALF_OPEN

                return True

            return False

        if self.state == CircuitState.HALF_OPEN:
            return True

    def record_success(self):

        self.failure_count = 0

        self.state = CircuitState.CLOSED

    def record_failure(self):

        self.failure_count += 1

        self.last_failure_time = time.time()

        print(
            f"[Circuit] Failure {self.failure_count}/{self.failure_threshold}"
        )

        if self.failure_count >= self.failure_threshold:

            self.state = CircuitState.OPEN

            print("[Circuit] OPENED")

    @property
    def is_open(self):

        return self.state == CircuitState.OPEN