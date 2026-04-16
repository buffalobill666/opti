"""
API роуты аутентификации.

POST /api/auth/login — вход
POST /api/auth/logout — выход
GET  /api/auth/status — проверка статуса
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ui.auth import verify_password
from utils.logger import logger

router = APIRouter()


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
async def login(request: Request, body: LoginRequest):
    """Вход через API."""
    if verify_password(body.password):
        request.session["authenticated"] = True
        request.session["user"] = "admin"
        logger.info("API вход выполнен успешно")
        return {"success": True, "message": "Аутентификация успешна"}

    logger.warning("Неверная попытка входа через API")
    return {"success": False, "message": "Неверный пароль"}


@router.post("/logout")
async def logout(request: Request):
    """Выход через API."""
    request.session.clear()
    logger.info("Выход через API")
    return {"success": True, "message": "Сессия завершена"}


@router.get("/status")
async def auth_status(request: Request):
    """Проверка статуса аутентификации."""
    return {
        "authenticated": request.session.get("authenticated", False),
        "user": request.session.get("user", "anonymous"),
    }
