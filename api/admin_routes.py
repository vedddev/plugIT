from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import key_store, require_admin

router = APIRouter(prefix="/admin/api-keys", tags=["API Key Management"])


class CreateKeyRequest(BaseModel):
    name: str
    expires_at: datetime | None = None
    metadata: str | None = None


@router.post("", dependencies=[Depends(require_admin)])
def create_key(request: CreateKeyRequest, user=Depends(require_admin)):
    record, plaintext = key_store.create(request.name, request.expires_at, request.metadata, None if user["id"] == "server-admin" else user["id"])
    return {**record, "key": plaintext}


@router.get("", dependencies=[Depends(require_admin)])
def list_keys(user=Depends(require_admin)):
    return {"data": key_store.list(None if user["id"] == "server-admin" else user["id"])}


@router.get("/{key_id}", dependencies=[Depends(require_admin)])
def get_key(key_id: str, user=Depends(require_admin)):
    record = key_store.get(key_id, None if user["id"] == "server-admin" else user["id"])
    if not record:
        raise HTTPException(status_code=404, detail="API key not found.")
    return record


@router.post("/{key_id}/revoke", dependencies=[Depends(require_admin)])
def revoke_key(key_id: str, user=Depends(require_admin)):
    record = key_store.revoke(key_id, None if user["id"] == "server-admin" else user["id"])
    if not record:
        raise HTTPException(status_code=404, detail="API key not found.")
    return record


@router.post("/{key_id}/rotate", dependencies=[Depends(require_admin)])
def rotate_key(key_id: str, user=Depends(require_admin)):
    result = key_store.rotate(key_id, None if user["id"] == "server-admin" else user["id"])
    if not result:
        raise HTTPException(status_code=404, detail="API key not found.")
    record, plaintext = result
    return {**record, "key": plaintext}
