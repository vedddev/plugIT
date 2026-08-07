from fastapi import Depends, Response

from api.auth import verify_api_key
from rate_limit.limiter import RateLimiter


limiter = RateLimiter(
    limit=60,
    window=60,
)


def rate_limit(
    response: Response,
    api_key: str = Depends(verify_api_key),
):
    result = limiter.check(api_key)

    response.headers["X-RateLimit-Limit"] = str(
        result["limit"]
    )

    response.headers["X-RateLimit-Remaining"] = str(
        result["remaining"]
    )

    response.headers["X-RateLimit-Reset"] = str(
        result["reset"]
    )

    return api_key