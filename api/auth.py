
import secrets

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()

# Temporary API keys.
# Later we can move these to Redis/database.
API_KEYS = {
    "sk-smartllm-dev": "developer",
}


def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
):
    api_key = credentials.credentials

    if not any(
        secrets.compare_digest(api_key, key)
        for key in API_KEYS
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )

    return API_KEYS[api_key]
