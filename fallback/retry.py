import time
from typing import Callable, TypeVar

T = TypeVar("T")


class RetryExecutor:
    """
    Generic retry executor with exponential backoff.
    """

    def __init__(
        self,
        retries: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: tuple = (Exception,),
    ):
        self.retries = retries
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions

    def run(self, func: Callable[..., T], *args, **kwargs) -> T:

        current_delay = self.delay
        last_exception = None

        for attempt in range(1, self.retries + 1):

            try:
                return func(*args, **kwargs)

            except self.exceptions as e:

                last_exception = e

                print(
                    f"[Retry] Attempt {attempt}/{self.retries} failed."
                )

                if attempt == self.retries:
                    break

                print(
                    f"[Retry] Waiting {current_delay:.1f}s..."
                )

                time.sleep(current_delay)

                current_delay *= self.backoff

        raise last_exception