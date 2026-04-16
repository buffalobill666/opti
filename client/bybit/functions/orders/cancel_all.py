"""
Отмена всех активных ордеров на Bybit.

API: POST /v5/order/cancel-all
Документация: https://bybit-exchange.github.io/docs/v5/order/cancel-all

Для опционов используется category="option".

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    base_coin (str, optional): Базовая валюта — "BTC" или "ETH"
    symbol (str, optional): Конкретный символ

Возвращает:
    dict:
        - success (bool): Успешность операции
        - cancelled_count (int): Количество отменённых ордеров

Пример:
    result = await cancel_all_orders(client, base_coin="BTC")
    print(f"Отменено ордеров: {result['cancelled_count']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def cancel_all_orders(
    client,
    base_coin: str = None,
    symbol: str = None,
) -> dict:
    """
    Отмена всех активных ордеров.

    Args:
        client: Экземпляр BybitClient
        base_coin: "BTC" или "ETH"
        symbol: Конкретный символ

    Returns:
        dict с результатами

    Raises:
        Exception: При ошибке запроса к API
    """
    params = {"category": "option"}

    if base_coin:
        params["baseCoin"] = base_coin
    if symbol:
        params["symbol"] = symbol

    logger.info(
        f"Отмена всех ордеров: category=option | "
        f"baseCoin={base_coin or 'ALL'} | symbol={symbol or 'ALL'}"
    )

    result = await client.call_private(
        method="cancel_all_orders",
        params=params,
    )

    cancelled = result.get("success", False)

    logger.info(f"Отмена всех ордеров: {'успешно' if cancelled else 'неудачно'}")

    return {
        "success": cancelled,
        "cancelled_count": 1 if cancelled else 0,
    }
