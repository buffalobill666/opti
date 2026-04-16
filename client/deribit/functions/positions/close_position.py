"""
Закрытие позиции по опциону Deribit.

Создаёт рыночный ордер в противоположном направлении для закрытия позиции.

Параметры:
    client (DeribitClient): Экземпляр Deribit клиента
    instrument_name (str): Название инструмента
    amount (float, optional): Размер для закрытия (если None — закрывает всю позицию)

Возвращает:
    dict:
        - order_id (str): ID закрывающего ордера
        - instrument_name (str): Название инструмента
        - side (str): Направление закрытия
        - amount (float): Количество
        - order_state (str): Состояние ордера

Пример:
    result = await close_position(client, instrument_name="BTC-27DEC24-80000-C")
    print(f"Позиция закрыта: {result['order_id']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def close_position(
    client,
    instrument_name: str,
    amount: float = None,
) -> dict:
    """
    Закрытие позиции рыночным ордером.

    Args:
        client: Экземпляр DeribitClient
        instrument_name: Название инструмента
        amount: Размер для закрытия (None = вся позиция)

    Returns:
        dict с данными закрывающего ордера

    Raises:
        Exception: При ошибке запроса к API
    """
    # Получаем текущую позицию
    positions_result = await client.call_private(
        method="private/get_positions",
        params={
            "currency": instrument_name.split("-")[0],  # BTC или ETH
            "kind": "option",
        },
    )

    positions = positions_result if isinstance(positions_result, list) else []
    position = None
    for pos in positions:
        if pos.get("instrument_name") == instrument_name:
            position = pos
            break

    if not position:
        raise Exception(f"Нет открытой позиции по {instrument_name}")

    # Определяем сторону закрытия (противоположная)
    position_size = position.get("size", 0)
    close_size = amount or abs(position_size)

    # Deribit: size > 0 = buy, size < 0 = sell
    # Закрываем в противоположном направлении
    if position_size > 0:
        close_side = "sell"
    else:
        close_side = "buy"

    logger.info(
        f"Закрытие позиции: {instrument_name} | "
        f"side={close_side} | amount={close_size}"
    )

    # Создаём рыночный ордер
    method = "private/buy" if close_side == "buy" else "private/sell"

    result = await client.call_private(
        method=method,
        params={
            "instrument_name": instrument_name,
            "amount": close_size,
            "type": "market",
            "reduce_only": True,
        },
    )

    order_data = result.get("order", {})

    order = {
        "order_id": order_data.get("order_id"),
        "instrument_name": order_data.get("instrument_name"),
        "side": order_data.get("direction"),
        "amount": order_data.get("amount"),
        "order_state": order_data.get("order_state"),
        "average_price": order_data.get("average_price"),
        "filled_amount": order_data.get("filled_amount"),
    }

    logger.info(
        f"Позиция закрыта: {order['order_id']} | "
        f"side={order['side']} | amount={order['amount']}"
    )

    return order
