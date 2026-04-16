"""
API роуты ордеров.

GET    /api/orders/{exchange}            — активные ордера
POST   /api/orders/{exchange}            — создать ордер
PUT    /api/orders/{exchange}/{order_id} — изменить ордер
DELETE /api/orders/{exchange}/{order_id} — отменить ордер
GET    /api/orders/{exchange}/history    — история ордеров
GET    /api/orders/{exchange}/instruments — получить инструменты по активу
"""

import os
import re
import math
from datetime import datetime, timezone, date, timedelta
from fastapi import APIRouter, Request, HTTPException, Query

from ui.key_store import get_decrypted_keys
from ui.models import OrderRequest, AmendOrderRequest, CancelOrderRequest
from utils.logger import logger

router = APIRouter()


def _get_exchange_mode(exchange: str) -> dict:
    """
    Определить режим из .env.

    Bybit:
      - BYBIT_DEMO=true  -> demo
      - иначе BYBIT_TESTNET=true -> testnet
      - иначе mainnet
    Deribit:
      - DERIBIT_TESTNET=true -> testnet, иначе mainnet
    """
    if exchange == "bybit":
        demo = os.getenv("BYBIT_DEMO", "false").lower() == "true"
        testnet = os.getenv("BYBIT_TESTNET", "false").lower() == "true"
        if demo:
            return {"demo": True, "testnet": False, "network": "demo"}
        if testnet:
            return {"demo": False, "testnet": True, "network": "testnet"}
        return {"demo": False, "testnet": False, "network": "mainnet"}

    testnet = os.getenv("DERIBIT_TESTNET", "false").lower() == "true"
    return {"demo": False, "testnet": testnet, "network": "testnet" if testnet else "mainnet"}


def _get_keys_or_env(exchange: str, testnet: bool, is_demo: bool = False) -> dict | None:
    """Получить ключи из keys.json или fallback из .env."""
    from ui.key_store import load_keys

    # Проверяем use_main_as_test
    keys = load_keys()
    exchange_data = keys.get(exchange, {})
    use_main_as_test = exchange_data.get("use_main_as_test", False)

    # Для Bybit demo — отдельные ключи, use_main_as_test не применяем
    if exchange == "bybit" and is_demo:
        keys_result = get_decrypted_keys(exchange, is_demo=True)
        if keys_result:
            return keys_result
        # Fallback: demo ключи из .env (если заданы)
        api_key = os.getenv("BYBIT_DEMO_API_KEY", "")
        api_secret = os.getenv("BYBIT_DEMO_API_SECRET", "")
        if api_key and api_secret:
            logger.info("Используются ключи bybit (demo) из .env")
            return {"api_key": api_key, "api_secret": api_secret, "testnet": False, "is_demo": True}
        return None

    effective_testnet = testnet
    if testnet and use_main_as_test:
        effective_testnet = False
        logger.info(f"{exchange.upper()} use_main_as_test — используем mainnet ключи для testnet")

    keys_result = get_decrypted_keys(exchange, testnet=effective_testnet)
    if keys_result:
        return keys_result

    # Fallback: читаем из .env
    if exchange == "bybit":
        if effective_testnet:
            api_key = os.getenv("BYBIT_TEST_API_KEY", "")
            api_secret = os.getenv("BYBIT_TEST_API_SECRET", "")
        else:
            api_key = os.getenv("BYBIT_API_KEY", "")
            api_secret = os.getenv("BYBIT_API_SECRET", "")
    else:
        if effective_testnet:
            api_key = os.getenv("DERIBIT_TEST_CLIENT_ID", "")
            api_secret = os.getenv("DERIBIT_TEST_CLIENT_SECRET", "")
        else:
            api_key = os.getenv("DERIBIT_CLIENT_ID", "")
            api_secret = os.getenv("DERIBIT_CLIENT_SECRET", "")

    if api_key and api_secret:
        logger.info(f"Используются ключи {exchange} ({'testnet' if effective_testnet else 'mainnet'}) из .env")
        return {"api_key": api_key, "api_secret": api_secret, "testnet": effective_testnet}

    return None


# ─── Маппинг Time in Force ──────────────────────────────────────────

# Bybit → Deribit TIF маппинг
DERIBIT_TIF_MAP = {
    "GTC": "good_til_cancelled",
    "IOC": "immediate_or_cancel",
    "FOK": "fill_or_kill",
    "PostOnly": "good_til_cancelled",  # PostOnly для Deribit через флаг
}


def _map_tif_for_deribit(tif: str) -> str:
    """Маппинг TIF из формата Bybit в формат Deribit."""
    return DERIBIT_TIF_MAP.get(tif, "good_til_cancelled")


# ─── Вспомогательные функции для инструментов ───────────────────────

def _parse_deribit_instrument(instrument: dict) -> dict:
    """Парсинг инструмента Deribit в единый формат (устаревшая функция)."""
    from utils.option_classifier import classify_deribit_option
    
    # Преобразуем формат Deribit в формат для классификатора
    deribit_format = {
        "instrument_name": instrument.get("instrument_name", ""),
        "base_currency": instrument.get("base_currency", ""),
        "quote_currency": instrument.get("quote_currency", ""),
        "settlement_period": instrument.get("settlement_period", ""),
        "option_type": instrument.get("option_type", ""),
        "strike": instrument.get("strike"),
        "tick_size": instrument.get("tick_size", ""),
        "contract_size": instrument.get("contract_size", ""),
        "expiration_timestamp": instrument.get("expiration_timestamp", 0),
        "creation_timestamp": instrument.get("creation_timestamp", 0),
        "instrument_id": instrument.get("instrument_id"),
        "is_active": instrument.get("is_active", True),
        "min_trade_amount": instrument.get("min_trade_amount", 1),
    }
    
    result = classify_deribit_option(deribit_format)
    
    return {
        "symbol": result["symbol"],
        "base_coin": instrument.get("base_currency", ""),
        "strike": result["strike"],
        "option_type": result["optionsType"],
        "expiration": result["expiry_date"],
        "period": result["period_group"],
        "period_type": result["period_type"],
        "days_to_expiry": result["days_to_expiry"],
        "original_duration_days": result["original_duration_days"],
        "tick_size": instrument.get("tick_size", ""),
        "tick_value": instrument.get("tick_value", ""),
        "min_trade_amount": instrument.get("min_trade_amount", 1),
        "is_active": result["status"] == "Trading",
    }


def classify_deribit_option_from_dict(instrument: dict) -> dict:
    """Парсинг инструмента Deribit с новой классификацией."""
    from utils.option_classifier import classify_deribit_option
    
    # Преобразуем формат Deribit в формат для классификатора
    deribit_format = {
        "instrument_name": instrument.get("instrument_name", ""),
        "base_currency": instrument.get("base_currency", ""),
        "quote_currency": instrument.get("quote_currency", ""),
        "settlement_period": instrument.get("settlement_period", ""),
        "option_type": instrument.get("option_type", ""),
        "strike": instrument.get("strike"),
        "tick_size": instrument.get("tick_size", ""),
        "contract_size": instrument.get("contract_size", ""),
        "expiration_timestamp": instrument.get("expiration_timestamp", 0),
        "creation_timestamp": instrument.get("creation_timestamp", 0),
        "instrument_id": instrument.get("instrument_id"),
        "is_active": instrument.get("is_active", True),
        "min_trade_amount": instrument.get("min_trade_amount", 1),
    }
    
    result = classify_deribit_option(deribit_format)
    
    return {
        "symbol": result["symbol"],
        "base_coin": instrument.get("base_currency", ""),
        "strike": result["strike"],
        "option_type": result["optionsType"],
        "expiration": result["expiry_date"],
        "period": result["period_group"],
        "period_type": result["period_type"],
        "days_to_expiry": result["days_to_expiry"],
        "original_duration_days": result["original_duration_days"],
        "tick_size": instrument.get("tick_size", ""),
        "tick_value": instrument.get("tick_value", ""),
        "min_trade_amount": instrument.get("min_trade_amount", 1),
        "is_active": result["status"] == "Trading",
    }

def _days_to_expiry(expiration: datetime) -> int:
    """
    Дни до экспирации (по датам, без влияния времени суток/таймзоны).

    Для опционов с датой в символе (например, BTC-17APR26-...) время экспирации
    на бирже может быть не 00:00 UTC. Если считать через seconds/ceil, "daily"
    часто съезжает. Поэтому считаем как разницу календарных дат в UTC.
    """
    now = datetime.now(timezone.utc)
    return (expiration.date() - now.date()).days


def _compute_expiry_sets(expiry_dates: list[date]) -> dict[str, set[date]]:
    """
    Классифицировать период по дням до экспирации.
    
    УСТАРЕВШАЯ ФУНКЦИЯ - использовать utils.option_classifier
    
    Используем ceil — если до экспирации 1 день 2 часа, это 2 полных дня.

    daily: 0-1 дней (экспирация сегодня/завтра)
    weekly: 2-14 дней
    monthly: > 14 дней
    """
    # Bybit может возвращать инструменты в произвольном порядке, а системная дата/UTC
    # может быть сдвинута (особенно если сервис не перезапускали). Поэтому серии
    # строим от фактически доступных экспираций: берём самые ранние даты в ответе.
    upcoming = sorted({d for d in expiry_dates})

    daily = set(upcoming[:3])

    fridays = [d for d in upcoming if d.weekday() == 4]  # Monday=0 ... Friday=4
    weekly = set(fridays[:3])

    monthly: set[date] = set()
    if len(fridays) >= 3:
        anchor = fridays[2]
        for k in range(3):
            candidate = anchor + timedelta(days=28 * k)
            if candidate in upcoming:
                monthly.add(candidate)

    return {"daily": daily, "weekly": weekly, "monthly": monthly}


def _classify_period_detailed(instrument: dict, exchange: str) -> dict:
    """
    Детальная классификация инструмента с использованием 9 типов периодов.
    
    Args:
        instrument: dict инструмента с полями launch_time/delivery_time или creation_timestamp/expiration_timestamp
        exchange: "bybit" или "deribit"
    
    Returns:
        dict с полями period_type, period_group, original_duration_days, days_to_expiry
    """
    from utils.option_classifier import classify_bybit_option, classify_deribit_option
    
    if exchange == "bybit":
        result = classify_bybit_option(instrument)
        return {
            "period_type": result["period_type"],
            "period_group": result["period_group"],
            "original_duration_days": result["original_duration_days"],
            "days_to_expiry": result["days_to_expiry"],
        }
    else:
        result = classify_deribit_option(instrument)
        return {
            "period_type": result["period_type"],
            "period_group": result["period_group"],
            "original_duration_days": result["original_duration_days"],
            "days_to_expiry": result["days_to_expiry"],
        }


def _select_by_expiration(instruments: list, period_group: str, position: str) -> list:
    """
    Выбрать инструменты по позиции в группе периодов (daily/weekly/monthly).
    
    Использует новую систему классификации с 9 типами периодов.
    
    Args:
        instruments: Список инструментов с полями period_type, period_group
        period_group: Группа периодов ("daily", "weekly", "monthly")
        position: Позиция ("nearest", "middle", "farthest")
    
    Returns:
        Список инструментов выбранной позиции внутри группы периодов
    """
    from utils.option_classifier import filter_contracts_by_period
    
    # Используем новую функцию фильтрации
    filtered = filter_contracts_by_period(instruments, period_group, position)
    
    return filtered


@router.get("/{exchange}/instruments")
async def get_instruments(
    request: Request,
    exchange: str,
    asset: str = Query(default="BTC", description="Базовый актив: BTC, ETH или кастомный тикер"),
    period: str = Query(default="", description="Фильтр периода: daily, weekly, monthly"),
    position: str = Query(default="", description="Позиция: nearest, middle, farthest"),
    option_type: str = Query(default="", description="Фильтр типа опциона: C или P"),
):
    """
    Получить инструменты для указанной биржи и актива.

    Если period и position указаны — фильтруем и находим ближайшие.
    """
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")

    if exchange not in ("bybit", "deribit"):
        return {"success": False, "error": f"Неподдерживаемая биржа: {exchange}"}

    mode = _get_exchange_mode(exchange)
    testnet = mode["testnet"]
    is_demo = mode["demo"]

    try:
        from client.main_client import UnifiedClient

        keys = _get_keys_or_env(exchange, testnet=testnet, is_demo=is_demo)
        if not keys:
            net = "demo" if is_demo else ("testnet" if testnet else "mainnet")
            return {"success": False, "error": f"API ключи для {exchange} ({net}) не настроены"}

        client = UnifiedClient()

        if exchange == "bybit":
            client.init_bybit(
                api_key=keys["api_key"],
                api_secret=keys["api_secret"],
                testnet=testnet,
                demo=is_demo,
            )
            # Не фильтруем status на стороне API — иначе в день экспирации часть инструментов
            # становится Delivering и пропадает из списка.
            result = await client.get_instruments("bybit", base_coin=asset, status=None)
            instruments = result.get("instruments", [])
            # Парсим Bybit инструменты с новой классификацией
            parsed = []
            expiry_dates: list[date] = []
            for inst in instruments:
                name = inst.get("symbol", "")
                # Bybit формат: BTC-27DEC24-80000-C
                parts = name.split("-") if name else []
                expiration_str = parts[1] if len(parts) > 1 else ""
                strike_str = parts[2] if len(parts) > 2 else ""
                option_type = parts[3] if len(parts) > 3 else ""

                expiration = None
                try:
                    expiration = datetime.strptime(expiration_str, "%d%b%y").replace(tzinfo=timezone.utc)
                except (ValueError, IndexError):
                    pass

                days = _days_to_expiry(expiration) if expiration else None
                
                # Используем новую детальную классификацию
                classification = _classify_period_detailed(inst, "bybit")
                
                try:
                    strike = float(strike_str)
                except (ValueError, TypeError):
                    strike = 0

                parsed.append({
                    "symbol": name,
                    "base_coin": asset,
                    "strike": strike,
                    "option_type": option_type,
                    "expiration": expiration.isoformat() if expiration else None,
                    "period": classification["period_group"],  # Группа для совместимости
                    "period_type": classification["period_type"],  # Конкретный тип (9 типов)
                    "days_to_expiry": days,
                    "original_duration_days": classification["original_duration_days"],
                    "tick_size": inst.get("tick_size", ""),
                    "tick_value": inst.get("tick_value", ""),
                    "min_trade_amount": inst.get("lot_size", 1),
                    "is_active": inst.get("status") == "Trading",
                    "status": inst.get("status"),
                })

            # Формируем серии экспираций и проставляем period
            sets = _compute_expiry_sets(expiry_dates)
            for item in parsed:
                exp_iso = item.get("expiration")
                if not exp_iso:
                    continue
                try:
                    exp_date = datetime.fromisoformat(exp_iso.replace("Z", "+00:00")).date()
                except Exception:
                    continue

                if exp_date in sets["monthly"]:
                    item["period"] = "monthly"
                elif exp_date in sets["weekly"]:
                    item["period"] = "weekly"
                elif exp_date in sets["daily"]:
                    item["period"] = "daily"
                else:
                    item["period"] = "other"

            # Фильтруем статусы: Trading + Delivering + PreLaunch.
            # На Bybit часть ближайших/дальних экспираций может быть PreLaunch,
            # но пользователю нужно их видеть для выбора "nearest/middle/farthest".
            allowed_statuses = {"Trading", "Delivering", "PreLaunch"}
            parsed = [p for p in parsed if (p.get("status") in allowed_statuses)]
        else:
            client.init_deribit(
                client_id=keys["api_key"],
                client_secret=keys["api_secret"],
                testnet=testnet,
            )
            result = await client.get_instruments("deribit", currency=asset)
            instruments = result.get("instruments", [])
            # Парсим Deribit инструменты с новой классификацией
            parsed = []
            for inst in instruments:
                classified = classify_deribit_option_from_dict(inst)
                parsed.append(classified)

        # Фильтрация по Call/Put
        if option_type:
            want = option_type.upper()
            if want in ("C", "P"):
                parsed = [i for i in parsed if (i.get("option_type") or "").upper() == want]

        # Фильтрация по периоду и позиции (позиция выбирается по ДАТЕ экспирации)
        if period and position:
            parsed = _select_by_expiration(parsed, period, position)

        # Сортировка по дням до экспирации
        parsed.sort(key=lambda x: (x["days_to_expiry"] or 9999, x["strike"]))

        return {
            "success": True,
            "data": {
                "exchange": exchange,
                "asset": asset,
                "instruments": parsed,
                "total": len(parsed),
            },
        }

    except Exception as e:
        logger.error(f"Ошибка получения инструментов {exchange}: {e}")
        return {"success": False, "error": str(e)}


@router.get("/{exchange}")
async def get_open_orders(request: Request, exchange: str):
    """Получить активные ордера."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")

    if exchange not in ("bybit", "deribit"):
        return {"success": False, "error": f"Неподдерживаемая биржа: {exchange}"}

    mode = _get_exchange_mode(exchange)
    testnet = mode["testnet"]
    is_demo = mode["demo"]

    try:
        from client.main_client import UnifiedClient

        keys = _get_keys_or_env(exchange, testnet=testnet, is_demo=is_demo)
        if not keys:
            net = "demo" if is_demo else ("testnet" if testnet else "mainnet")
            return {"success": False, "error": f"API ключи для {exchange} ({net}) не настроены"}

        client = UnifiedClient()

        if exchange == "bybit":
            client.init_bybit(
                api_key=keys["api_key"],
                api_secret=keys["api_secret"],
                testnet=testnet,
                demo=is_demo,
            )
            result = await client.get_order_history("bybit", base_coin="BTC", order_status="New")
        else:
            client.init_deribit(
                client_id=keys["api_key"],
                client_secret=keys["api_secret"],
                testnet=testnet,
            )
            result = await client.get_order_history("deribit", currency="ALL", count=50)

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Ошибка получения ордеров {exchange}: {e}")
        return {"success": False, "error": str(e)}


@router.post("/{exchange}")
async def create_order(request: Request, exchange: str, body: OrderRequest):
    """Создать ордер."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")

    if exchange not in ("bybit", "deribit"):
        return {"success": False, "error": f"Неподдерживаемая биржа: {exchange}"}

    mode = _get_exchange_mode(exchange)
    testnet = mode["testnet"]
    is_demo = mode["demo"]

    try:
        from client.main_client import UnifiedClient

        keys = _get_keys_or_env(exchange, testnet=testnet, is_demo=is_demo)
        if not keys:
            net = "demo" if is_demo else ("testnet" if testnet else "mainnet")
            return {"success": False, "error": f"API ключи для {exchange} ({net}) не настроены"}

        client = UnifiedClient()

        if exchange == "bybit":
            client.init_bybit(
                api_key=keys["api_key"],
                api_secret=keys["api_secret"],
                testnet=testnet,
                demo=is_demo,
            )
            # Для Market ордеров Bybit не передаём price
            order_params = {
                "symbol": body.symbol,
                "side": body.side,
                "order_type": body.order_type,
                "qty": body.qty,
                "time_in_force": body.time_in_force,
                "order_link_id": body.order_link_id,
                "reduce_only": body.reduce_only,
                "close_on_trigger": body.close_on_trigger,
                "order_iv": body.order_iv,
                "mmp": body.mmp,
                "take_profit": body.take_profit,
                "stop_loss": body.stop_loss,
                "tp_limit_price": body.tp_limit_price,
                "sl_limit_price": body.sl_limit_price,
                "tp_trigger_by": body.tp_trigger_by,
                "sl_trigger_by": body.sl_trigger_by,
            }
            if body.order_type == "Limit" and body.price:
                order_params["price"] = body.price

            result = await client.create_order("bybit", **order_params)
        else:
            client.init_deribit(
                client_id=keys["api_key"],
                client_secret=keys["api_secret"],
                testnet=testnet,
            )
            # Для Deribit: маппинг TIF и lowercase type
            deribit_tif = _map_tif_for_deribit(body.time_in_force)
            deribit_type = body.order_type.lower()

            # Для Market ордеров Deribit не передаём price
            order_params = {
                "instrument_name": body.symbol,
                "side": body.side.lower(),
                "amount": float(body.qty),
                "type": deribit_type,
                "time_in_force": deribit_tif,
                "reduce_only": body.reduce_only,
                "post_only": body.post_only,
                "label": body.label,
                "advanced": body.advanced,
                "trigger_price": float(body.trigger_price) if body.trigger_price else None,
                "trigger_offset": float(body.trigger_offset) if body.trigger_offset else None,
                "trigger": body.trigger,
                "mmp": body.mmp,
            }
            if body.order_type == "Limit" and body.price:
                order_params["price"] = float(body.price)

            result = await client.create_order("deribit", **order_params)

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Ошибка создания ордера {exchange}: {e}")
        return {"success": False, "error": str(e)}


@router.put("/{exchange}/{order_id}")
async def amend_order(request: Request, exchange: str, order_id: str, body: AmendOrderRequest):
    """Изменить ордер."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")

    if exchange not in ("bybit", "deribit"):
        return {"success": False, "error": f"Неподдерживаемая биржа: {exchange}"}

    testnet = _get_testnet(exchange)

    try:
        from client.main_client import UnifiedClient

        keys = _get_keys_or_env(exchange, testnet=testnet)
        if not keys:
            net = "testnet" if testnet else "mainnet"
            return {"success": False, "error": f"API ключи для {exchange} ({net}) не настроены"}

        client = UnifiedClient()

        if exchange == "bybit":
            client.init_bybit(
                api_key=keys["api_key"],
                api_secret=keys["api_secret"],
                testnet=testnet,
            )
            result = await client.amend_order(
                "bybit",
                symbol=body.symbol,
                order_id=order_id,
                price=body.price,
                qty=body.qty,
            )
        else:
            client.init_deribit(
                client_id=keys["api_key"],
                client_secret=keys["api_secret"],
                testnet=testnet,
            )
            result = await client.amend_order(
                "deribit",
                order_id=order_id,
                price=body.price,
                amount=float(body.qty) if body.qty else None,
            )

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Ошибка изменения ордера {exchange}: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/{exchange}/{order_id}")
async def cancel_order(request: Request, exchange: str, order_id: str):
    """Отменить ордер."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")

    if exchange not in ("bybit", "deribit"):
        return {"success": False, "error": f"Неподдерживаемая биржа: {exchange}"}

    testnet = _get_testnet(exchange)

    try:
        from client.main_client import UnifiedClient

        keys = _get_keys_or_env(exchange, testnet=testnet)
        if not keys:
            net = "testnet" if testnet else "mainnet"
            return {"success": False, "error": f"API ключи для {exchange} ({net}) не настроены"}

        client = UnifiedClient()

        if exchange == "bybit":
            client.init_bybit(
                api_key=keys["api_key"],
                api_secret=keys["api_secret"],
                testnet=testnet,
            )
            result = await client.cancel_order("bybit", symbol="", order_id=order_id)
        else:
            client.init_deribit(
                client_id=keys["api_key"],
                client_secret=keys["api_secret"],
                testnet=testnet,
            )
            result = await client.cancel_order("deribit", order_id=order_id)

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Ошибка отмены ордера {exchange}: {e}")
        return {"success": False, "error": str(e)}


@router.get("/{exchange}/history")
async def get_order_history(request: Request, exchange: str, limit: int = 50):
    """Получить историю ордеров."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")

    if exchange not in ("bybit", "deribit"):
        return {"success": False, "error": f"Неподдерживаемая биржа: {exchange}"}

    testnet = _get_testnet(exchange)

    try:
        from client.main_client import UnifiedClient

        keys = _get_keys_or_env(exchange, testnet=testnet)
        if not keys:
            net = "testnet" if testnet else "mainnet"
            return {"success": False, "error": f"API ключи для {exchange} ({net}) не настроены"}

        client = UnifiedClient()

        if exchange == "bybit":
            client.init_bybit(
                api_key=keys["api_key"],
                api_secret=keys["api_secret"],
                testnet=testnet,
            )
            result = await client.get_order_history("bybit", base_coin="BTC", limit=limit)
        else:
            client.init_deribit(
                client_id=keys["api_key"],
                client_secret=keys["api_secret"],
                testnet=testnet,
            )
            result = await client.get_order_history("deribit", currency="ALL", count=limit)

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Ошибка истории ордеров {exchange}: {e}")
        return {"success": False, "error": str(e)}
