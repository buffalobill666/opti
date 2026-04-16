"""
Утилита для шифрованного хранения API ключей.

Использует cryptography.fernet для шифрования.
Ключ шифрования ВСЕГДА деривируется из APP_SECRET_KEY через SHA-256.

Структура хранения (config/keys.json):
{
    "bybit": {
        "mainnet": {"api_key": "encrypted...", "api_secret": "encrypted..."},
        "testnet": {"api_key": "encrypted...", "api_secret": "encrypted..."},
        "demo":    {"api_key": "encrypted...", "api_secret": "encrypted..."},
        "use_main_as_test": false
    },
    "deribit": {
        "mainnet": {"api_key": "encrypted...", "api_secret": "encrypted..."},
        "testnet": {"api_key": "encrypted...", "api_secret": "encrypted..."},
        "use_main_as_test": false
    }
}
"""

import os
import json
from pathlib import Path

from cryptography.fernet import Fernet

from utils.logger import logger


CONFIG_DIR = Path("config")
CONFIG_DIR.mkdir(exist_ok=True)

KEYS_FILE = CONFIG_DIR / "keys.json"


def _get_fernet() -> Fernet:
    """
    Получение Fernet объекта для шифрования.

    Ключ ВСЕГДА деривируется из APP_SECRET_KEY через SHA-256.
    Это гарантирует одинаковый ключ при шифровании и расшифровке.

    Returns:
        Fernet объект
    """
    import base64
    import hashlib

    secret = os.getenv("APP_SECRET_KEY", "optionsrunner_default_secret_key_2024")

    # ВСЕГДА деривируем ключ — гарантирует стабильность
    digest = hashlib.sha256(secret.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_value(value: str) -> str:
    """
    Шифрование значения.

    Args:
        value: Значение для шифрования

    Returns:
        str: Зашифрованное значение (base64)
    """
    fernet = _get_fernet()
    return fernet.encrypt(value.encode()).decode()


def decrypt_value(encrypted: str) -> str:
    """
    Расшифровка значения.

    Args:
        encrypted: Зашифрованное значение

    Returns:
        str: Расшифрованное значение
    """
    fernet = _get_fernet()
    return fernet.decrypt(encrypted.encode()).decode()


def _mask_key(key: str, show_last: int = 4) -> str:
    """Маскирует ключ, показывая только последние N символов."""
    if not key or len(key) <= show_last:
        return "****"
    return "****" + key[-show_last:]


def _mask_key_prefix(key: str, show_first: int = 4) -> str:
    """Маскирует ключ, показывая только первые N символов."""
    if not key or len(key) <= show_first:
        return "****"
    return key[:show_first] + "****"


def save_keys(exchange: str, api_key: str, api_secret: str, testnet: bool = False, is_demo: bool = False):
    """
    Сохранение API ключей в зашифрованном виде для указанной сети.

    Args:
        exchange: "bybit" или "deribit"
        api_key: API ключ
        api_secret: API секрет
        testnet: Флаг testnet — ключи сохраняются отдельно для каждой сети
        is_demo: True = demo ключи (только Bybit)
    """
    keys = load_keys()

    # Инициализируем структуру если нужно
    if exchange not in keys:
        keys[exchange] = {"mainnet": {}, "testnet": {}, "demo": {}, "use_main_as_test": False}

    if is_demo:
        net = "demo"
    else:
        net = "testnet" if testnet else "mainnet"

    keys[exchange][net] = {
        "api_key": encrypt_value(api_key),
        "api_secret": encrypt_value(api_secret),
    }

    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)

    logger.info(
        f"API ключи сохранены для {exchange} ({net})"
    )


def save_keys_partial(exchange: str, api_key: str | None, api_secret: str | None,
                      testnet: bool = False, is_demo: bool = False):
    """
    Частичное сохранение — обновляет только переданные поля.

    Args:
        exchange: "bybit" или "deribit"
        api_key: API ключ (None = не менять)
        api_secret: API секрет (None = не менять)
        testnet: False = mainnet, True = testnet
        is_demo: True = demo
    """
    keys = load_keys()

    if exchange not in keys:
        keys[exchange] = {"mainnet": {}, "testnet": {}, "demo": {}, "use_main_as_test": False}

    if is_demo:
        net = "demo"
    else:
        net = "testnet" if testnet else "mainnet"

    if net not in keys[exchange]:
        keys[exchange][net] = {}

    if api_key:
        keys[exchange][net]["api_key"] = encrypt_value(api_key)
    if api_secret:
        keys[exchange][net]["api_secret"] = encrypt_value(api_secret)

    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)

    logger.info(
        f"API ключи частично обновлены для {exchange} ({net})"
    )


def load_keys() -> dict:
    """
    Загрузка всех API ключей.

    Returns:
        dict: Словарь с ключами для каждой биржи и сети
    """
    if not KEYS_FILE.exists():
        return {}

    try:
        with open(KEYS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Миграция: добавляем demo и use_main_as_test если нет
            for exch in ("bybit", "deribit"):
                if exch in data:
                    if "demo" not in data[exch]:
                        data[exch]["demo"] = {}
                    if "use_main_as_test" not in data[exch]:
                        data[exch]["use_main_as_test"] = False
            return data
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Ошибка загрузки ключей: {e}")
        return {}


def get_decrypted_keys(exchange: str, testnet: bool = False, is_demo: bool = False) -> dict | None:
    """
    Получение расшифрованных ключей для биржи и сети.

    Args:
        exchange: "bybit" или "deribit"
        testnet: True = testnet, False = mainnet
        is_demo: True = demo (только Bybit)

    Returns:
        dict: {"api_key": ..., "api_secret": ...} или None
    """
    keys = load_keys()
    exchange_data = keys.get(exchange, {})

    if is_demo:
        net = "demo"
    elif testnet:
        # Если use_main_as_test — берём mainnet ключи
        if exchange_data.get("use_main_as_test", False):
            net = "mainnet"
        else:
            net = "testnet"
    else:
        net = "mainnet"

    net_data = exchange_data.get(net, {})

    if not net_data.get("api_key"):
        return None

    try:
        return {
            "api_key": decrypt_value(net_data["api_key"]),
            "api_secret": decrypt_value(net_data["api_secret"]),
            "testnet": testnet,
            "is_demo": is_demo,
        }
    except Exception as e:
        logger.error(f"Ошибка расшифровки ключей {exchange} ({net}): {e}")
        return None


def get_masked_keys() -> dict:
    """
    Получение маскированных ключей для отображения (все сети + .env инфо).

    Returns:
        dict: {
            "bybit": {
                "mainnet": {"api_key": "abc****", "api_secret": "****xyz", "configured": True},
                "testnet": {"api_key": "xyz****", "api_secret": "****abc", "configured": False},
                "demo":    {"api_key": "", "api_secret": "", "configured": False},
                "use_main_as_test": false,
                "env_configured": true,
                "env_api_key": "abc****",
                "env_api_secret": "****xyz"
            },
            ...
        }
    """
    keys = load_keys()
    masked = {}

    for exchange in ("bybit", "deribit"):
        exchange_data = keys.get(exchange, {})
        masked[exchange] = {}

        for net in ("mainnet", "testnet", "demo"):
            net_data = exchange_data.get(net, {})
            api_key_enc = net_data.get("api_key", "")

            if api_key_enc:
                try:
                    decrypted = decrypt_value(api_key_enc)
                    masked_key = _mask_key_prefix(decrypted, 4)
                    masked_secret = _mask_key(decrypted, 4) if api_key_enc else "****"
                    configured = True
                except Exception:
                    masked_key = "****"
                    masked_secret = "****"
                    configured = False
            else:
                masked_key = ""
                masked_secret = ""
                configured = False

            # Для secret показываем только последние 4 знака
            api_secret_enc = net_data.get("api_secret", "")
            if api_secret_enc and configured:
                try:
                    decrypted_secret = decrypt_value(api_secret_enc)
                    masked_secret = _mask_key(decrypted_secret, 4)
                except Exception:
                    masked_secret = "****"

            masked[exchange][net] = {
                "api_key": masked_key,
                "api_secret": masked_secret,
                "configured": configured,
            }

        # Флаг use_main_as_test
        masked[exchange]["use_main_as_test"] = exchange_data.get("use_main_as_test", False)

        # Информация о .env ключах
        env_key = os.getenv(f"{exchange.upper()}_API_KEY", "")
        env_secret = os.getenv(f"{exchange.upper()}_API_SECRET", "")
        # Для deribit — CLIENT_ID / CLIENT_SECRET
        if exchange == "deribit":
            env_key = os.getenv("DERIBIT_CLIENT_ID", "")
            env_secret = os.getenv("DERIBIT_CLIENT_SECRET", "")

        masked[exchange]["env_configured"] = bool(env_key and env_secret)
        masked[exchange]["env_api_key"] = _mask_key_prefix(env_key, 4) if env_key else ""
        masked[exchange]["env_api_secret"] = _mask_key(env_secret, 4) if env_secret else ""

        # Demo .env ключи (Bybit)
        if exchange == "bybit":
            demo_key = os.getenv("BYBIT_DEMO_API_KEY", "")
            demo_secret = os.getenv("BYBIT_DEMO_API_SECRET", "")
            masked[exchange]["env_demo_configured"] = bool(demo_key and demo_secret)
            masked[exchange]["env_demo_api_key"] = _mask_key_prefix(demo_key, 4) if demo_key else ""
            masked[exchange]["env_demo_api_secret"] = _mask_key(demo_secret, 4) if demo_secret else ""
        else:
            masked[exchange]["env_demo_configured"] = False
            masked[exchange]["env_demo_api_key"] = ""
            masked[exchange]["env_demo_api_secret"] = ""

    return masked


def delete_keys(exchange: str, testnet: bool | None = None, is_demo: bool = False):
    """
    Удаление ключей.

    Args:
        exchange: "bybit" или "deribit"
        testnet: None = удалить все сети, True/False = удалить конкретную сеть
        is_demo: True = удалить demo ключи
    """
    keys = load_keys()

    if exchange not in keys:
        return

    if testnet is None and not is_demo:
        # Удалить все сети
        del keys[exchange]
        logger.info(f"API ключи удалены для {exchange} (все сети)")
    else:
        if is_demo:
            net = "demo"
        elif testnet is not None:
            net = "testnet" if testnet else "mainnet"
        else:
            net = "mainnet"

        if net in keys[exchange]:
            del keys[exchange][net]
            logger.info(f"API ключи удалены для {exchange} ({net})")

    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)


def update_network(exchange: str, testnet: bool):
    """
    Обновление флага testnet (используется для UI).

    Args:
        exchange: "bybit" или "deribit"
        testnet: Новый флаг testnet
    """
    net = "testnet" if testnet else "mainnet"
    keys = load_keys()
    exchange_data = keys.get(exchange, {})
    net_data = exchange_data.get(net, {})

    if net_data.get("api_key"):
        logger.info(f"{exchange.upper()} переключён на {net} (ключи найдены)")
    else:
        logger.info(f"{exchange.upper()} переключён на {net} (ключи НЕ настроены)")


def set_use_main_as_test(exchange: str, use_main_as_test: bool):
    """
    Установка флага использования mainnet ключей для testnet.

    Args:
        exchange: "bybit" или "deribit"
        use_main_as_test: True = использовать mainnet ключи для testnet
    """
    keys = load_keys()

    if exchange not in keys:
        keys[exchange] = {"mainnet": {}, "testnet": {}, "demo": {}, "use_main_as_test": False}

    keys[exchange]["use_main_as_test"] = use_main_as_test

    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)

    logger.info(
        f"{exchange.upper()} use_main_as_test = {use_main_as_test}"
    )
