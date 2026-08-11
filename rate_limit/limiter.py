import time

from redis import Redis
from errors.exceptions import RateLimitError


class RateLimiter:

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        limit: int = 60,
        window: int = 60,
    ):
        self.redis = Redis.from_url(
            redis_url,
            decode_responses=True,
        )

        self.limit = limit
        self.window = window

    def check(self, api_key: str):
        key = f"rate_limit:{api_key}"

        current = self.redis.incr(key)

        if current == 1:
            self.redis.expire(key, self.window)

        ttl = self.redis.ttl(key)

        remaining = max(self.limit - current, 0)

        if current > self.limit:
            raise RateLimitError("Rate limit exceeded.")

        return {
            "limit": self.limit,
            "remaining": remaining,
            "reset": max(ttl, 0),
        }
