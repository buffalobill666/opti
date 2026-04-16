"""
API роуты управления API ключами и переключения сети.

GET    /api/keys                      — получить маскированные ключи (все сети + .env)
POST   /api/keys                      — сохранить полные ключи
PATCH  /api/keys                      — частичное обновление (только указанные поля)
DELETE /api/keys/{exchange}           — удалить ключи
POST   /api/keys/test                 — тест подключения
POST   /api/keys/network              — переключить testnet/mainnet (сохранить в .env)
GET    /api/keys/network/{exchange}   — получить текущую сеть и конфиг
POST   /api/keys/use-main-as-test     — установить флаг use_main_as_test
"""

import os
import re

from fastapi import APIRouter, Request, HTTPException

from ui.key_store import (
    save_keys,
    save_keys_partial,
    get_masked_keys,
    delete_keys,
    get_decrypted_keys,
    update_network,
    set_use_main_as_test,
)
from ui.models import APICredentials, APICredentialsPartial, NetworkSwitch, TestConnectionRequest
from utils.logger import logger

router = APIRouter()

# ─── Работа с .env файлом ──────────────────────────────────────────

# Абсолютный путь к .env в корне проекта
from pathlib import Path
_ENV_FILE = str(Path(__file__).parent.parent.parent / ".env")


def _read_env_file() -> dict:
    """Прочитать .env файл и вернуть все переменные."""
    env_vars = {}
    env_path = _ENV_FILE
    if not os.path.exists(env_path):
        return env_vars

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    return env_vars


def _write_env_var(var_name: str, var_value: str):
    """Изменить или добавить переменную в .env файл."""
    env_path = _ENV_FILE
    env_content = ""

    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            env_content = f.read()

    # Ищем строку с переменной и заменяем
    pattern = rf"^{re.escape(var_name)}\s*=.*$"
    replacement = f"{var_name}={var_value}"

    if re.search(pattern, env_content, re.MULTILINE):
        env_content = re.sub(pattern, replacement, env_content, flags=re.MULTILINE)
    else:
        # Добавляем в конец
        env_content = env_content.rstrip() + f"\n{replacement}\n"

    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)

    # Обновляем os.environ
    os.environ[var_name] = var_value
    logger.info(f".env обновлён: {var_name}={var_value}")


@router.get("")
async def get_keys(request: Request):
    """Получить маскированные API ключи для всех сетей + информация о .env."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")

    masked = get_masked_keys()

    return {
        "success": True,
        "data": masked,
    }


@router.post("")
async def save_api_keys(request: Request, body: APICredentials):
    """Сохранить полные API ключи для указанной сети."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")

    if body.exchange not in ("bybit", "deribit"):
        return {"success": False, "error": f"Неподдерживаемая биржа: {body.exchange}"}

    if not body.api_key or not body.api_secret:
        return {"success": False, "error": "Заполните оба поля (ключ и секрет)"}

    save_keys(
        exchange=body.exchange,
        api_key=body.api_key,
        api_secret=body.api_secret,
        testnet=body.testnet,
    )

    net = "testnet" if body.testnet else "mainnet"
    return {
        "success": True,
        "message": f"Ключи сохранены для {body.exchange} ({net})",
    }


@router.patch("")
async def update_api_keys_partial(request: Request, body: APICredentialsPartial):
    """Частичное обновление ключей — можно передать только одно поле."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")

    if body.exchange not in ("bybit", "deribit"):
        return {"success": False, "error": f"Неподдерживаемая биржа: {body.exchange}"}

    if not body.api_key and not body.api_secret:
        return {"success": False, "error": "Укажите хотя бы одно поле для обновления"}

    save_keys_partial(
        exchange=body.exchange,
        api_key=body.api_key,
        api_secret=body.api_secret,
        testnet=body.testnet,
        is_demo=body.is_demo,
    )

    if body.is_demo:
        net = "demo"
    else:
        net = "testnet" if body.testnet else "mainnet"

    return {
        "success": True,
        "message": f"Ключи обновлены для {body.exchange} ({net})",
    }


@router.delete("/{exchange}")
async def delete_api_keys(request: Request, exchange: str, testnet: bool = False, is_demo: bool = False):
    """Удалить API ключи для биржи и сети."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")

    if exchange not in ("bybit", "deribit"):
        return {"success": False, "error": f"Неподдерживаемая биржа: {exchange}"}

    delete_keys(exchange, testnet=testnet if not is_demo else None, is_demo=is_demo)

    if is_demo:
        net = "demo"
    elif testnet:
        net = "testnet"
    else:
        net = "mainnet"

    return {
        "success": True,
        "message": f"Ключи удалены для {exchange} ({net})",
    }


@router.post("/test")
async def test_connection(request: Request, body: TestConnectionRequest):
    """Тестирование подключения к бирже."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")

    try:
        if body.exchange == "bybit":
            from client.bybit.bybit_client import BybitClient

            client = BybitClient(
                api_key=body.api_key,
                api_secret=body.api_secret,
                testnet=body.testnet,
                demo=body.is_demo,
            )
            # Тестовый запрос — получение инструментов
            await client.call_public(
                method="get_instruments_info",
                params={"category": "option", "baseCoin": "BTC", "limit": "1"},
            )
            if body.is_demo:
                network = "demo"
            elif body.testnet:
                network = "testnet"
            else:
                network = "mainnet"
            return {
                "success": True,
                "message": f"Подключение к Bybit {network} успешно",
                "exchange": "bybit",
                "network": network,
            }

        elif body.exchange == "deribit":
            from client.deribit.deribit_client import DeribitClient

            client = DeribitClient(
                client_id=body.api_key,
                client_secret=body.api_secret,
                testnet=body.testnet,
            )
            await client.authenticate()
            network = "testnet" if body.testnet else "mainnet"
            return {
                "success": True,
                "message": f"Подключение к Deribit {network} успешно",
                "exchange": "deribit",
                "network": network,
            }

        else:
            return {"success": False, "error": f"Неподдерживаемая биржа: {body.exchange}"}

    except Exception as e:
        logger.error(f"Ошибка тестирования {body.exchange}: {e}")
        return {
            "success": False,
            "message": f"Ошибка подключения: {str(e)}",
            "exchange": body.exchange,
            "network": "demo" if body.is_demo else ("testnet" if body.testnet else "mainnet"),
        }


@router.post("/network")
async def switch_network(request: Request, body: NetworkSwitch):
    """
    Переключить testnet/mainnet — физически меняет .env флаги.

    Для Bybit:
        testnet=true  → BYBIT_DEMO=true (используем demo сеть)
        testnet=false → BYBIT_DEMO=false (используем mainnet)

    Для Deribit:
        testnet=true  → DERIBIT_TESTNET=true
        testnet=false → DERIBIT_TESTNET=false
    """
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")

    if body.exchange not in ("bybit", "deribit"):
        return {"success": False, "error": f"Неподдерживаемая биржа: {body.exchange}"}

    if body.exchange == "bybit":
        # Для Bybit: testnet = demo режим
        _write_env_var("BYBIT_DEMO", str(body.testnet).lower())
        network_name = "demo" if body.testnet else "mainnet"
    else:
        # Для Deribit: testnet = testnet режим
        _write_env_var("DERIBIT_TESTNET", str(body.testnet).lower())
        network_name = "testnet" if body.testnet else "mainnet"

    # Логируем переключение
    update_network(body.exchange, body.testnet)

    return {
        "success": True,
        "message": f"{body.exchange} переключён на {network_name} (.env обновлён)",
        "exchange": body.exchange,
        "network": network_name,
    }


@router.post("/use-main-as-test")
async def set_use_main_as_test_flag(request: Request, body: dict):
    """Установить флаг использования mainnet ключей для testnet."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")

    exchange = body.get("exchange")
    use_main_as_test = body.get("use_main_as_test", False)

    if exchange not in ("bybit", "deribit"):
        return {"success": False, "error": f"Неподдерживаемая биржа: {exchange}"}

    set_use_main_as_test(exchange, use_main_as_test)

    status = "включён" if use_main_as_test else "выключен"
    return {
        "success": True,
        "message": f"{exchange.upper()} Use Main As Test {status}",
        "exchange": exchange,
        "use_main_as_test": use_main_as_test,
    }


@router.get("/network/{exchange}")
async def get_network_status(request: Request, exchange: str):
    """Получить текущую сеть и статус ключей для биржи."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Требуется аутентификация")

    if exchange not in ("bybit", "deribit"):
        return {"success": False, "error": f"Неподдерживаемая биржа: {exchange}"}

    # Проверяем наличие ключей для всех сетей
    masked = get_masked_keys()
    exchange_data = masked.get(exchange, {})

    mainnet_configured = exchange_data.get("mainnet", {}).get("configured", False)
    testnet_configured = exchange_data.get("testnet", {}).get("configured", False)
    demo_configured = exchange_data.get("demo", {}).get("configured", False)
    use_main_as_test = exchange_data.get("use_main_as_test", False)

    # Определяем текущую активную сеть — ЧИТАЕМ НАПРЯМУЮ ИЗ .env ФАЙЛА
    env_vars = _read_env_file()

    if exchange == "bybit":
        bybit_demo = env_vars.get("BYBIT_DEMO", "false").lower() == "true"
        bybit_testnet = env_vars.get("BYBIT_TESTNET", "false").lower() == "true"
        if bybit_demo:
            current_network = "demo"
        elif bybit_testnet:
            current_network = "testnet"
        else:
            current_network = "mainnet"
    else:
        deribit_testnet = env_vars.get("DERIBIT_TESTNET", "false").lower() == "true"
        current_network = "testnet" if deribit_testnet else "mainnet"

    # URL
    mainnet_url = "https://api.bybit.com" if exchange == "bybit" else "https://www.deribit.com/api/v2"
    testnet_url = "https://api-testnet.bybit.com" if exchange == "bybit" else "https://test.deribit.com/api/v2"
    demo_url = "https://api-demo.bybit.com" if exchange == "bybit" else None

    # .env информация
    env_configured = exchange_data.get("env_configured", False)
    env_api_key = exchange_data.get("env_api_key", "")
    env_api_secret = exchange_data.get("env_api_secret", "")

    # Demo .env (только Bybit)
    env_demo_configured = exchange_data.get("env_demo_configured", False)
    env_demo_api_key = exchange_data.get("env_demo_api_key", "")
    env_demo_api_secret = exchange_data.get("env_demo_api_secret", "")

    return {
        "success": True,
        "data": {
            "exchange": exchange,
            "current_network": current_network,
            "mainnet": {
                "configured": mainnet_configured,
                "url": mainnet_url,
            },
            "testnet": {
                "configured": testnet_configured,
                "url": testnet_url,
            },
            "demo": {
                "configured": demo_configured,
                "url": demo_url,
            },
            "use_main_as_test": use_main_as_test,
            "env": {
                "configured": env_configured,
                "api_key": env_api_key,
                "api_secret": env_api_secret,
            },
            "env_demo": {
                "configured": env_demo_configured,
                "api_key": env_demo_api_key,
                "api_secret": env_demo_api_secret,
            },
        },
    }
