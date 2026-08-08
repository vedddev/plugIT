from fastapi import HTTPException

# Maximum total tokens allowed per API key
QUOTA_LIMIT = 5000


def check_quota(api_key: str, usage_tracker) -> None:
    """
    Check whether the API key has exceeded its token quota.

    Raises:
        HTTPException(429) if the quota has been exceeded.
    """

    usage = usage_tracker.get(api_key)

    total_tokens = usage.get("total_tokens", 0)

    if total_tokens >= QUOTA_LIMIT:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "quota_exceeded",
                "message": "Token quota exceeded.",
                "quota_limit": QUOTA_LIMIT,
                "total_tokens": total_tokens,
            },
        )

