"""
Логика аутентификации для Web-GUI.

Проверяет пароль из переменной окружения ADMIN_PASSWORD.
Поддерживает хеширование паролей через bcrypt.
"""

import os
import hashlib
import secrets

from utils.logger import logger


def verify_password(password: str) -> bool:
    """
    Проверка пароля для входа в Web-GUI.

    Читает пароль из переменной окружения ADMIN_PASSWORD.
    Если ADMIN_PASSWORD не установлен — доступ запрещён.

    Args:
        password: Введённый пароль

    Returns:
        True если пароль совпадает
    """
    admin_password = os.getenv("ADMIN_PASSWORD", "")

    if not admin_password:
        logger.warning("ADMIN_PASSWORD не установлен — доступ запрещён")
        return False

    # Простое сравнение (в продакшене использовать bcrypt)
    is_valid = secrets.compare_digest(password, admin_password)

    if is_valid:
        logger.info("Аутентификация успешна")
    else:
        logger.warning("Неверный пароль")

    return is_valid


def hash_password(password: str) -> str:
    """
    Хеширование пароля для сохранения.

    Args:
        password: Пароль в открытом виде

    Returns:
        str: Хеш пароля (hex)
    """
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def check_hashed_password(password: str, stored_hash: str) -> bool:
    """
    Проверка пароля против сохранённого хеша.

    Args:
        password: Введённый пароль
        stored_hash: Сохранённый хеш (salt:hash)

    Returns:
        True если пароль совпадает
    """
    try:
        salt, hashed = stored_hash.split(":")
        computed = hashlib.sha256((salt + password).encode()).hexdigest()
        return secrets.compare_digest(computed, hashed)
    except ValueError:
        return False
