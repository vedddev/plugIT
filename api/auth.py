
import secrets
import os

from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from errors.exceptions import AuthenticationError
from key_management.store import APIKeyStore

security = HTTPBearer()

key_store = APIKeyStore()


def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
):
    api_key = credentials.credentials
    # Development compatibility is explicitly configured, never hard-coded.
    dev_key = os.getenv("SMARTLLM_API_KEY")
    if os.getenv("SMARTLLM_ENV", "development").lower() == "development" and dev_key:
        if secrets.compare_digest(api_key, dev_key):
            return "developer"
    return key_store.authenticate(api_key)["id"]
