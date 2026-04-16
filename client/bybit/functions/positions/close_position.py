"""
Закрытие позиции по опциону Bybit.

Создаёт рыночный ордер в противоположном направлении для закрытия позиции.

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    symbol (str): Символ инструмента
    size (str, optional): Размер для закрытия (если None — закрывает всю позицию)

Возвращает:
    dict:
        - order_id (str): ID закрывающего ордера
        - symbol (str): Символ инструмента
        - side (str): Направление закрытия
        - qty (str): Количество
        - status (str): Состояние ордера

Пример:
    result = await close_position(client, symbol="BTC-27DEC24-80000-C")
    print(f"Позиция закрыта: {result['order_id']}")
"""

import uuid

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def close_position(
    client,
    symbol: str,
    size: str = None,
) -> dict:
    """
    Закрытие позиции рыночным ордером.

    Args:
        client: Экземпляр BybitClient
        symbol: Символ инструмента
        size: Размер для закрытия (None = вся позиция)

    Returns:
        dict с данными закрывающего ордера

    Raises:
        Exception: При ошибке запроса к API
    """
    # Получаем текущую позицию
    positions_result = await client.call_private(
        method="get_positions",
        params={"category": "option", "symbol": symbol},
    )

    positions = positions_result.get("list", [])
    if not positions:
        raise Exception(f"Нет открытой позиции по {symbol}")

    position = positions[0]
    position_side = position.get("side")
    position_size = position.get("size", "0")

    # Определяем сторону закрытия (противоположная)
    close_side = "Sell" if position_side == "Buy" else "Buy"
    close_size = size or position_size

    logger.info(
        f"Закрытие позиции: {symbol} | "
        f"side={close_side} | size={close_size}"
    )

    # Создаём рыночный ордер
    result = await client.call_private(
        method="place_order",
        params={
            "category": "option",
            "symbol": symbol,
            "side": close_side,
            "orderType": "Market",
            "qty": close_size,
            "reduceOnly": True,
            "orderLinkId": f"close_{uuid.uuid4().hex[:12]}",
        },
    )

    order = {
        "order_id": result.get("orderId"),
        "symbol": result.get("symbol"),
        "side": result.get("side"),
        "qty": result.get("qty"),
        "status": result.get("orderStatus"),
    }

    logger.info(
        f"Позиция закрыта: {order['order_id']} | "
        f"side={order['side']} | qty={order['qty']}"
    )

    return order
