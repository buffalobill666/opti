"""
API роуты для управления стратегиями.

GET    /api/strategies          — получить все стратегии
GET    /api/strategies/{id}     — получить стратегию по ID
POST   /api/strategies          — создать стратегию
PUT    /api/strategies/{id}     — обновить стратегию
DELETE /api/strategies/{id}     — удалить стратегию
POST   /api/strategies/{id}/toggle — переключить статус
"""

from fastapi import APIRouter, Request, HTTPException

from ui.models import StrategyCreate, StrategyUpdate
from ui.strategy_store import (
    get_all_strategies,
    get_strategy,
    create_strategy,
    update_strategy,
    delete_strategy,
    toggle_strategy_status,
)
from utils.logger import logger

router = APIRouter()


def _require_auth(request: Request):
    """Проверка аутентификации."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")


@router.get("")
async def api_get_all_strategies(request: Request):
    """Получить все стратегии."""
    _require_auth(request)

    try:
        strategies = await get_all_strategies()
        return {
            "success": True,
            "data": [s.model_dump() for s in strategies],
            "total": len(strategies),
        }
    except Exception as e:
        logger.error(f"Ошибка получения стратегий: {e}")
        return {"success": False, "error": str(e)}


@router.get("/{strategy_id}")
async def api_get_strategy(request: Request, strategy_id: str):
    """Получить стратегию по ID."""
    _require_auth(request)

    try:
        strategy = await get_strategy(strategy_id)
        if not strategy:
            return {"success": False, "error": "Стратегия не найдена"}
        return {"success": True, "data": strategy.model_dump()}
    except Exception as e:
        logger.error(f"Ошибка получения стратегии {strategy_id}: {e}")
        return {"success": False, "error": str(e)}


@router.post("")
async def api_create_strategy(request: Request, data: StrategyCreate):
    """Создать новую стратегию."""
    _require_auth(request)

    try:
        strategy = await create_strategy(data)
        return {"success": True, "data": strategy.model_dump()}
    except Exception as e:
        logger.error(f"Ошибка создания стратегии: {e}")
        return {"success": False, "error": str(e)}


@router.put("/{strategy_id}")
async def api_update_strategy(request: Request, strategy_id: str, data: StrategyUpdate):
    """Обновить стратегию."""
    _require_auth(request)

    try:
        strategy = await update_strategy(strategy_id, data)
        if not strategy:
            return {"success": False, "error": "Стратегия не найдена"}
        return {"success": True, "data": strategy.model_dump()}
    except Exception as e:
        logger.error(f"Ошибка обновления стратегии {strategy_id}: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/{strategy_id}")
async def api_delete_strategy(request: Request, strategy_id: str):
    """Удалить стратегию."""
    _require_auth(request)

    try:
        result = await delete_strategy(strategy_id)
        if not result:
            return {"success": False, "error": "Стратегия не найдена"}
        return {"success": True, "message": "Стратегия удалена"}
    except Exception as e:
        logger.error(f"Ошибка удаления стратегии {strategy_id}: {e}")
        return {"success": False, "error": str(e)}


@router.post("/{strategy_id}/toggle")
async def api_toggle_strategy(request: Request, strategy_id: str):
    """Переключить статус активности стратегии."""
    _require_auth(request)

    try:
        strategy = await toggle_strategy_status(strategy_id)
        if not strategy:
            return {"success": False, "error": "Стратегия не найдена"}
        return {
            "success": True,
            "data": strategy.model_dump(),
            "message": f"Стратегия {'активна' if strategy.is_active else 'неактивна'}",
        }
    except Exception as e:
        logger.error(f"Ошибка переключения стратегии {strategy_id}: {e}")
        return {"success": False, "error": str(e)}
