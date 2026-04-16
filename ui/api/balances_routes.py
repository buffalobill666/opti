"""
API роуты балансов.

GET /api/balances/{exchange}        — получить балансы
GET /api/balances/{exchange}/summary — сводка
"""

import os
from fastapi import APIRouter, Request, HTTPException

from ui.key_store import get_decrypted_keys
from utils.logger import logger

router = APIRouter()


def _get_testnet(exchange: str) -> bool:
    """Определить testnet из .env для биржи."""
    if exchange == "bybit":
        return os.getenv("BYBIT_TESTNET", "false").lower() == "true"
    return os.getenv("DERIBIT_TESTNET", "false").lower() == "true"


def _get_demo(exchange: str) -> bool:
    """Определить demo mode из .env для биржи."""
    if exchange == "bybit":
        return os.getenv("BYBIT_DEMO", "false").lower() == "true"
    return False


def _get_keys_or_env(exchange: str, testnet: bool, demo: bool = False) -> dict | None:
    """Получить ключи из keys.json или fallback из .env."""
    from ui.key_store import load_keys

    if demo:
        # Demo Trading — сначала ищем сохранённые demo ключи
        demo_keys = get_decrypted_keys(exchange, testnet=False, is_demo=True)
        if demo_keys:
            logger.info(f"Используются сохранённые Demo ключи {exchange}")
            return {**demo_keys, "demo": True}

        # Fallback — читаем напрямую из .env
        api_key = os.getenv("BYBIT_DEMO_API_KEY", "")
        api_secret = os.getenv("BYBIT_DEMO_API_SECRET", "")
        if api_key and api_secret:
            logger.info(f"Используются Demo ключи {exchange} из .env")
            return {"api_key": api_key, "api_secret": api_secret, "testnet": False, "demo": True}
        return None

    # Проверяем use_main_as_test
    keys = load_keys()
    exchange_data = keys.get(exchange, {})
    use_main_as_test = exchange_data.get("use_main_as_test", False)

    effective_testnet = testnet
    if testnet and use_main_as_test:
        effective_testnet = False  # Используем mainnet ключи
        logger.info(f"{exchange.upper()} use_main_as_test — используем mainnet ключи для testnet")

    keys_result = get_decrypted_keys(exchange, testnet=effective_testnet, is_demo=False)
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
        return {"api_key": api_key, "api_secret": api_secret, "testnet": effective_testnet, "demo": False}

    return None


@router.get("/{exchange}")
async def get_balances(request: Request, exchange: str):
    """Получить балансы для указанной биржи."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")

    if exchange not in ("bybit", "deribit"):
        return {"success": False, "error": f"Неподдерживаемая биржа: {exchange}"}

    testnet = _get_testnet(exchange)
    demo = _get_demo(exchange)

    try:
        from client.main_client import UnifiedClient

        keys = _get_keys_or_env(exchange, testnet=testnet, demo=demo)
        if not keys:
            net = "demo" if demo else ("testnet" if testnet else "mainnet")
            return {"success": False, "error": f"API ключи для {exchange} ({net}) не настроены"}

        client = UnifiedClient()

        if exchange == "bybit":
            client.init_bybit(
                api_key=keys["api_key"],
                api_secret=keys["api_secret"],
                testnet=testnet,
                demo=demo,
            )
            result = await client.get_balances("bybit", account_type="UNIFIED")
        else:
            client.init_deribit(
                client_id=keys["api_key"],
                client_secret=keys["api_secret"],
                testnet=testnet,
            )
            result = await client.get_balances("deribit", currency="BTC")

        return {"success": True, "data": result}

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            net = "testnet" if testnet else "mainnet"
            logger.warning(f"Невалидные API ключи для {exchange} ({net})")
            return {
                "success": False,
                "error": f"Невалидные API ключи {exchange} ({net}). Проверьте ключи на странице API Ключи.",
            }
        logger.error(f"Ошибка получения балансов {exchange}: {e}")
        return {"success": False, "error": str(e)}


@router.get("/{exchange}/summary")
async def get_balances_summary(request: Request, exchange: str):
    """Получить сводку по балансам."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")

    if exchange not in ("bybit", "deribit"):
        return {"success": False, "error": f"Неподдерживаемая биржа: {exchange}"}

    testnet = _get_testnet(exchange)
    demo = _get_demo(exchange)

    try:
        from client.main_client import UnifiedClient

        keys = _get_keys_or_env(exchange, testnet=testnet, demo=demo)
        if not keys:
            net = "demo" if demo else ("testnet" if testnet else "mainnet")
            return {"success": False, "error": f"API ключи для {exchange} ({net}) не настроены"}

        client = UnifiedClient()

        if exchange == "bybit":
            client.init_bybit(
                api_key=keys["api_key"],
                api_secret=keys["api_secret"],
                testnet=testnet,
                demo=demo,
            )
            result = await client.get_balances("bybit", account_type="UNIFIED")
            # Сводка
            balances = result.get("balances", [])
            total_equity = sum(float(b.get("equity", 0)) for b in balances)
            total_available = sum(float(b.get("available_to_withdraw", 0)) for b in balances)

            return {
                "success": True,
                "data": {
                    "exchange": "bybit",
                    "total_equity_usd": total_equity,
                    "total_available_usd": total_available,
                    "coins": balances,
                },
            }
        else:
            client.init_deribit(
                client_id=keys["api_key"],
                client_secret=keys["api_secret"],
                testnet=testnet,
            )
            result = await client.get_balances("deribit", currency="BTC")
            balances = result.get("balances", [])

            total_equity = sum(float(b.get("equity", 0)) for b in balances) if balances else 0
            total_available = sum(float(b.get("available_funds", 0)) for b in balances) if balances else 0

            return {
                "success": True,
                "data": {
                    "exchange": "deribit",
                    "total_equity": total_equity,
                    "total_available": total_available,
                    "coins": balances,
                },
            }

    except Exception as e:
        logger.error(f"Ошибка сводки балансов {exchange}: {e}")
        return {"success": False, "error": str(e)}
