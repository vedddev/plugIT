import time

from redis import Redis


class UsageTracker:

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
    ):
        self.redis = Redis.from_url(
            redis_url,
            decode_responses=True,
        )

    def _key(self, api_key: str) -> str:
        return f"usage:{api_key}"

    def record(
        self,
        api_key: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        cost: float = 0.0,
        success: bool = True,
    ):
        key = self._key(api_key)

        pipe = self.redis.pipeline()

        pipe.hincrby(key, "requests", 1)

        if success:
            pipe.hincrby(key, "successful_requests", 1)
        else:
            pipe.hincrby(key, "failed_requests", 1)

        pipe.hincrby(
            key,
            "input_tokens",
            input_tokens,
        )

        pipe.hincrby(
            key,
            "output_tokens",
            output_tokens,
        )

        pipe.hincrby(
            key,
            "total_tokens",
            total_tokens,
        )

        pipe.hincrbyfloat(
            key,
            "cost",
            cost,
        )

        pipe.hset(
            key,
            "last_request",
            int(time.time()),
        )

        pipe.execute()

    def get(self, api_key: str) -> dict:
        key = self._key(api_key)

        data = self.redis.hgetall(key)

        return {
            "requests": int(data.get("requests", 0)),
            "successful_requests": int(
                data.get("successful_requests", 0)
            ),
            "failed_requests": int(
                data.get("failed_requests", 0)
            ),
            "input_tokens": int(
                data.get("input_tokens", 0)
            ),
            "output_tokens": int(
                data.get("output_tokens", 0)
            ),
            "total_tokens": int(
                data.get("total_tokens", 0)
            ),
            "cost": float(
                data.get("cost", 0.0)
            ),
            "last_request": (
                int(data["last_request"])
                if "last_request" in data
                else None
            ),
        }