"""
API роуты рыночных данных.

GET /api/market/{exchange}/instruments      — список инструментов
GET /api/market/{exchange}/orderbook/{symbol} — стакан
GET /api/market/{exchange}/tickers/{base_coin} — тикеры
GET /api/market/{exchange}/kline/{symbol}   — свечи
"""

import os
import time
from fastapi import APIRouter, Request, HTTPException

from ui.key_store import get_decrypted_keys
from utils.logger import logger

router = APIRouter()


def _get_testnet(exchange: str) -> bool:
    """Определить testnet из .env для биржи."""
    if exchange == "bybit":
        return os.getenv("BYBIT_TESTNET", "false").lower() == "true"
    return os.getenv("DERIBIT_TESTNET", "false").lower() == "true"


def _get_keys_or_env(exchange: str, testnet: bool) -> dict | None:
    """Получить ключи из keys.json или fallback из .env."""
    from ui.key_store import load_keys

    # Проверяем use_main_as_test
    keys = load_keys()
    exchange_data = keys.get(exchange, {})
    use_main_as_test = exchange_data.get("use_main_as_test", False)

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


@router.get("/{exchange}/instruments")
async def get_instruments(request: Request, exchange: str, base_coin: str = "BTC"):
    """Получить список инструментов."""
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
            result = await client.get_instruments("bybit", base_coin=base_coin)
        else:
            client.init_deribit(
                client_id=keys["api_key"],
                client_secret=keys["api_secret"],
                testnet=testnet,
            )
            result = await client.get_instruments("deribit", currency=base_coin)

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Ошибка получения инструментов {exchange}: {e}")
        return {"success": False, "error": str(e)}


@router.get("/{exchange}/orderbook/{symbol}")
async def get_orderbook(request: Request, exchange: str, symbol: str, depth: int = 10):
    """Получить стакан."""
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
            result = await client.get_orderbook("bybit", symbol=symbol, limit=depth)
        else:
            client.init_deribit(
                client_id=keys["api_key"],
                client_secret=keys["api_secret"],
                testnet=testnet,
            )
            result = await client.get_orderbook("deribit", instrument_name=symbol, depth=depth)

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Ошибка получения стакана {exchange}: {e}")
        return {"success": False, "error": str(e)}


@router.get("/{exchange}/tickers/{base_coin}")
async def get_tickers(request: Request, exchange: str, base_coin: str = "BTC"):
    """Получить тикеры."""
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
            result = await client.get_tickers("bybit", base_coin=base_coin)
        else:
            client.init_deribit(
                client_id=keys["api_key"],
                client_secret=keys["api_secret"],
                testnet=testnet,
            )
            result = await client.get_tickers("deribit", currency=base_coin)

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Ошибка получения тикеров {exchange}: {e}")
        return {"success": False, "error": str(e)}


@router.get("/{exchange}/kline/{symbol}")
async def get_kline(
    request: Request,
    exchange: str,
    symbol: str,
    interval: str = "60",
    limit: int = 100,
):
    """Получить свечи."""
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
            result = await client.get_kline("bybit", symbol=symbol, interval=interval, limit=limit)
        else:
            client.init_deribit(
                client_id=keys["api_key"],
                client_secret=keys["api_secret"],
                testnet=testnet,
            )
            end_time = int(time.time() * 1000)
            start_time = end_time - (limit * int(interval) * 60 * 1000)
            result = await client.get_kline(
                "deribit",
                instrument_name=symbol,
                start_timestamp=start_time,
                end_timestamp=end_time,
                resolution=interval,
            )

        return {"success": True, "data": result}

    except Exception as e:
        logger.error(f"Ошибка получения свечей {exchange}: {e}")
        return {"success": False, "error": str(e)}
