"""
Декоратор для замера времени выполнения функций.

Использует time.perf_counter() для точного замера.
Автоматически определяет async/sync функцию.
Логирует начало, завершение и время через loguru.
"""

import time
import asyncio
from functools import wraps
from loguru import logger


def timed_execution(func):
    """
    Декоратор для замера времени выполнения функции.

    Логирует:
      - ▶ Начало: <func_name>
      - ✓ Завершено: <func_name> | <elapsed>s
      - ✗ Ошибка: <func_name> | <elapsed>s | <Exception>

    Работает с async и sync функциями.
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.debug(f"▶ Начало: {func_name}")
        start_time = time.perf_counter()

        try:
            result = await func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time
            logger.debug(f"✓ Завершено: {func_name} | {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error(
                f"✗ Ошибка: {func_name} | {elapsed:.3f}s | "
                f"{type(e).__name__}: {e}"
            )
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.debug(f"▶ Начало: {func_name}")
        start_time = time.perf_counter()

        try:
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start_time
            logger.debug(f"✓ Завершено: {func_name} | {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error(
                f"✗ Ошибка: {func_name} | {elapsed:.3f}s | "
                f"{type(e).__name__}: {e}"
            )
            raise

    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
