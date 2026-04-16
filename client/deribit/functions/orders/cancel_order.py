"""
Отмена ордера Deribit.

API: private/cancel
Документация: https://docs.deribit.com/api-reference/trading/private-cancel

Параметры:
    client (DeribitClient): Экземпляр Deribit клиента
    order_id (str): ID ордера для отмены

Возвращает:
    dict:
        - order_id (str): ID отменённого ордера
        - instrument_name (str): Название инструмента
        - order_state (str): Состояние — "cancelled"
        - order_type (str): Тип ордера
        - direction (str): Направление — "buy" или "sell"
        - price (float): Цена ордера
        - amount (float): Запрошенный объём
        - filled_amount (float): Заполненный объём до отмены
        - average_price (float): Средняя цена заполнения
        - commission (float): Комиссия
        - creation_timestamp (int): Время создания (мс)
        - last_update_timestamp (int): Время отмены (мс)

Пример:
    result = await cancel_order(client, order_id="12345")
    print(f"Order {result['order_id']} cancelled, state: {result['order_state']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def cancel_order(client, order_id: str) -> dict:
    """
    Отмена активного ордера по ID.

    Args:
        client: Экземпляр DeribitClient
        order_id: ID ордера для отмены

    Returns:
        dict с данными отменённого ордера

    Raises:
        Exception: При ошибке запроса к API (напр., ордер уже заполнен или отменён)
    """
    logger.info(f"Отмена ордера: {order_id}")

    result = await client.call_private(
        method="private/cancel",
        params={"order_id": order_id}
    )

    order_data = result

    order = {
        "order_id": order_data.get("order_id"),
        "instrument_name": order_data.get("instrument_name"),
        "order_state": order_data.get("order_state"),
        "order_type": order_data.get("order_type"),
        "direction": order_data.get("direction"),
        "price": order_data.get("price"),
        "amount": order_data.get("amount"),
        "filled_amount": order_data.get("filled_amount"),
        "average_price": order_data.get("average_price"),
        "commission": order_data.get("commission"),
        "creation_timestamp": order_data.get("creation_timestamp"),
        "last_update_timestamp": order_data.get("last_update_timestamp"),
    }

    logger.info(
        f"Ордер отменён: {order['order_id']} | "
        f"state={order['order_state']} | "
        f"filled={order['filled_amount']}/{order['amount']}"
    )

    return order
