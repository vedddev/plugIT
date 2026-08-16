import os
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from api.auth import (SESSION_COOKIE, authenticate_user, create_session, create_user,
                      current_user, public_user, revoke_session)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: str
    password: str


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(SESSION_COOKIE, token, httponly=True, secure=os.getenv("SMARTLLM_ENV", "development").lower() == "production",
                        samesite="lax", max_age=30 * 24 * 60 * 60, path="/")


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, response: Response):
    user = create_user(payload.email, payload.password, payload.name or "")
    set_session_cookie(response, create_session(user["id"]))
    return user


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    user = authenticate_user(payload.email, payload.password)
    set_session_cookie(response, create_session(user["id"]))
    return public_user(user)


@router.get("/me")
def me(user=__import__("fastapi").Depends(current_user)):
    return public_user(user)


@router.post("/logout", status_code=204)
def logout(response: Response, rim_session: str | None = __import__("fastapi").Cookie(default=None)):
    revoke_session(rim_session)
    response.delete_cookie(SESSION_COOKIE, path="/")
