import os
import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from api.auth import key_store
from errors.exceptions import AuthenticationError

router = APIRouter(prefix="/admin/api-keys", tags=["API Key Management"])


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("SMARTLLM_ADMIN_KEY")
    if not expected or not x_admin_key or not secrets.compare_digest(x_admin_key, expected):
        raise AuthenticationError("Invalid admin credentials.")


class CreateKeyRequest(BaseModel):
    name: str
    expires_at: datetime | None = None
    metadata: str | None = None


@router.post("", dependencies=[Depends(require_admin)])
def create_key(request: CreateKeyRequest):
    record, plaintext = key_store.create(request.name, request.expires_at, request.metadata)
    return {**record, "key": plaintext}


@router.get("", dependencies=[Depends(require_admin)])
def list_keys():
    return {"data": key_store.list()}


@router.get("/{key_id}", dependencies=[Depends(require_admin)])
def get_key(key_id: str):
    record = key_store.get(key_id)
    if not record:
        raise HTTPException(status_code=404, detail="API key not found.")
    return record


@router.post("/{key_id}/revoke", dependencies=[Depends(require_admin)])
def revoke_key(key_id: str):
    record = key_store.revoke(key_id)
    if not record:
        raise HTTPException(status_code=404, detail="API key not found.")
    return record


@router.post("/{key_id}/rotate", dependencies=[Depends(require_admin)])
def rotate_key(key_id: str):
    result = key_store.rotate(key_id)
    if not result:
        raise HTTPException(status_code=404, detail="API key not found.")
    record, plaintext = result
    return {**record, "key": plaintext}
