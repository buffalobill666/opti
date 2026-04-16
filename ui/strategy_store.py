"""
Хранилище стратегий.

Сохраняет и загружает стратегии из JSON файла.
Потокобезопасное через asyncio.Lock.

Файл: config/strategies.json
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from ui.models import Strategy, StrategyCreate, StrategyUpdate
from utils.logger import logger

# ─── Путь к файлу ───────────────────────────────────────────────────

STRATEGIES_FILE = Path(__file__).parent.parent / "config" / "strategies.json"
_lock = asyncio.Lock()


def _ensure_file():
    """Создать файл если не существует."""
    STRATEGIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not STRATEGIES_FILE.exists():
        STRATEGIES_FILE.write_text("[]", encoding="utf-8")
        logger.info("Создан файл стратегий: strategies.json")


def _load_all() -> list[dict]:
    """Загрузить все стратегии из файла."""
    _ensure_file()
    try:
        data = json.loads(STRATEGIES_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Ошибка чтения файла стратегий: {e}")
        return []


def _save_all(strategies: list[dict]):
    """Сохранить все стратегии в файл."""
    _ensure_file()
    STRATEGIES_FILE.write_text(
        json.dumps(strategies, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _to_strategy(data: dict) -> Strategy:
    """Конвертировать dict в Strategy."""
    return Strategy(**data)


def _from_strategy(s: Strategy) -> dict:
    """Конвертировать Strategy в dict для сохранения."""
    return s.model_dump()


# ─── CRUD операции ──────────────────────────────────────────────────

async def get_all_strategies() -> list[Strategy]:
    """Получить все стратегии."""
    async with _lock:
        data = _load_all()
        return [_to_strategy(d) for d in data]


async def get_strategy(strategy_id: str) -> Optional[Strategy]:
    """Получить стратегию по ID."""
    async with _lock:
        data = _load_all()
        for d in data:
            if d.get("id") == strategy_id:
                return _to_strategy(d)
        return None


async def create_strategy(create_data: StrategyCreate) -> Strategy:
    """Создать новую стратегию."""
    async with _lock:
        data = _load_all()

        now = datetime.now().isoformat()
        strategy = Strategy(
            id=str(uuid4())[:12],
            name=create_data.name,
            description=create_data.description,
            asset_type=create_data.asset_type,
            custom_asset=create_data.custom_asset,
            volume=create_data.volume,
            volume_currency=create_data.volume_currency,
            volume_split=create_data.volume_split,
            split_count=create_data.split_count,
            contracts=[c.model_dump() if hasattr(c, 'model_dump') else c for c in create_data.contracts],
            entry_type=create_data.entry_type,
            entry_webhook=create_data.entry_webhook if create_data.entry_webhook else {},
            stop_loss=create_data.stop_loss if create_data.stop_loss else {},
            take_profit=create_data.take_profit if create_data.take_profit else {},
            created_at=now,
            updated_at=now,
            is_active=create_data.is_active,
        )

        # Конвертируем вложенные модели в dict
        s_dict = _from_strategy(strategy)

        data.append(s_dict)
        _save_all(data)

        logger.info(f"Создана стратегия: {strategy.name} ({strategy.id})")
        return strategy


async def update_strategy(strategy_id: str, update_data: StrategyUpdate) -> Optional[Strategy]:
    """Обновить существующую стратегию."""
    async with _lock:
        data = _load_all()

        for i, d in enumerate(data):
            if d.get("id") == strategy_id:
                # Обновляем поля
                update_dict = update_data.model_dump(exclude_unset=True)
                for key, value in update_dict.items():
                    if hasattr(value, 'model_dump'):
                        d[key] = value.model_dump()
                    else:
                        d[key] = value

                d["updated_at"] = datetime.now().isoformat()
                data[i] = d
                _save_all(data)

                strategy = _to_strategy(d)
                logger.info(f"Обновлена стратегия: {strategy.name} ({strategy.id})")
                return strategy

        return None


async def delete_strategy(strategy_id: str) -> bool:
    """Удалить стратегию."""
    async with _lock:
        data = _load_all()
        new_data = [d for d in data if d.get("id") != strategy_id]

        if len(new_data) == len(data):
            return False  # Не найдена

        _save_all(new_data)
        logger.info(f"Удалена стратегия: {strategy_id}")
        return True


async def toggle_strategy_status(strategy_id: str) -> Optional[Strategy]:
    """Переключить статус активности стратегии."""
    async with _lock:
        data = _load_all()

        for i, d in enumerate(data):
            if d.get("id") == strategy_id:
                d["is_active"] = not d.get("is_active", True)
                d["updated_at"] = datetime.now().isoformat()
                data[i] = d
                _save_all(data)

                strategy = _to_strategy(d)
                status = "активна" if strategy.is_active else "неактивна"
                logger.info(f"Стратегия {strategy.name} ({strategy.id}) — {status}")
                return strategy

        return None
