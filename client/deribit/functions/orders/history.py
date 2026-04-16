"""
Получение истории ордеров Deribit.

API: private/get_order_history
Документация: https://docs.deribit.com/api-reference/trading/private-get_order_history

Параметры:
    client (DeribitClient): Экземпляр Deribit клиента
    currency (str): Базовая валюта — "BTC", "ETH" или "ALL"
    count (int): Количество записей (макс 1000, по умолчанию 10)
    offset (int): Смещение для пагинации (по умолчанию 0)

Возвращает:
    list[dict]: Список ордеров с полями:
        - order_id (str): ID ордера
        - instrument_name (str): Название инструмента
        - direction (str): Направление — "buy" или "sell"
        - order_type (str): Тип ордера
        - order_state (str): Состояние — "filled", "cancelled", "rejected"
        - price (float): Цена ордера
        - amount (float): Запрошенный объём
        - filled_amount (float): Заполненный объём
        - average_price (float): Средняя цена заполнения
        - commission (float): Комиссия
        - creation_timestamp (int): Время создания (мс)
        - last_update_timestamp (int): Время последнего обновления (мс)
        - time_in_force (str): Время действия — "GTC", "IOC", "FOK"
        - reduce_only (bool): Флаг reduce-only
        - post_only (bool): Флаг post-only
        - label (str): Метка ордера

Пример:
    # Последние 50 ордеров по BTC
    orders = await get_order_history(client, currency="BTC", count=50)
    for order in orders:
        print(f"{order['order_id']} | {order['instrument_name']} | "
              f"{order['order_state']} | {order['average_price']}")

    # Пагинация — следующие 50
    orders = await get_order_history(client, currency="BTC", count=50, offset=50)
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_order_history(
    client,
    currency: str = "ALL",
    count: int = 10,
    offset: int = 0
) -> list:
    """
    Получение истории ордеров для указанной валюты.

    Args:
        client: Экземпляр DeribitClient
        currency: "BTC", "ETH" или "ALL"
        count: Количество записей (макс 1000)
        offset: Смещение для пагинации

    Returns:
        list[dict] с данными ордеров

    Raises:
        ValueError: Если currency невалидна или count > 1000
        Exception: При ошибке запроса к API
    """
    if currency not in ("BTC", "ETH", "ALL"):
        raise ValueError(
            f"Неподдерживаемая валюта: {currency}. "
            f"Используйте 'BTC', 'ETH' или 'ALL'"
        )
    if count > 1000:
        raise ValueError(f"Максимальное количество записей: 1000. Получено: {count}")

    logger.info(
        f"Запрос истории ордеров: {currency} | "
        f"count={count} | offset={offset}"
    )

    result = await client.call_private(
        method="private/get_order_history",
        params={
            "currency": currency,
            "count": count,
            "offset": offset,
        }
    )

    orders = []
    for item in result:
        orders.append({
            "order_id": item.get("order_id"),
            "instrument_name": item.get("instrument_name"),
            "direction": item.get("direction"),
            "order_type": item.get("order_type"),
            "order_state": item.get("order_state"),
            "price": item.get("price"),
            "amount": item.get("amount"),
            "filled_amount": item.get("filled_amount"),
            "average_price": item.get("average_price"),
            "commission": item.get("commission"),
            "creation_timestamp": item.get("creation_timestamp"),
            "last_update_timestamp": item.get("last_update_timestamp"),
            "time_in_force": item.get("time_in_force"),
            "reduce_only": item.get("reduce_only"),
            "post_only": item.get("post_only"),
            "label": item.get("label"),
        })

    logger.info(
        f"Получено ордеров: {len(orders)} | "
        f"currency={currency} | offset={offset}"
    )

    return orders
