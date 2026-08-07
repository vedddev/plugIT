import time

from fastapi import HTTPException
from redis import Redis


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
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later.",
                headers={
                    "Retry-After": str(max(ttl, 1)),
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(max(ttl, 0)),
                },
            )

        return {
            "limit": self.limit,
            "remaining": remaining,
            "reset": max(ttl, 0),
        }