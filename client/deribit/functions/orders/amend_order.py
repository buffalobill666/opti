"""
Изменение существующего ордера Deribit.

API: private/edit
Документация: https://docs.deribit.com/api-reference/trading/private-edit

Параметры:
    client (DeribitClient): Экземпляр Deribit клиента
    order_id (str): ID ордера для изменения
    amount (float, optional): Новый объём (количество контрактов)
    price (float, optional): Новая цена
    post_only (bool, optional): Флаг post-only
    advanced (str, optional): "usd" для расчёта в USD
    stop_price (float, optional): Новая цена триггера для стоп-ордеров

Возвращает:
    dict:
        - order_id (str): ID ордера
        - order_state (str): Состояние ордера
        - order_type (str): Тип ордера
        - instrument_name (str): Название инструмента
        - price (float): Обновлённая цена
        - amount (float): Обновлённый объём
        - filled_amount (float): Заполненный объём
        - average_price (float): Средняя цена заполнения
        - last_update_timestamp (int): Время последнего обновления (мс)

Пример:
    # Изменить цену ордера
    updated = await amend_order(
        client,
        order_id="12345",
        price=1600
    )
    print(f"Order {updated['order_id']} updated, new price: {updated['price']}")

    # Изменить объём
    updated = await amend_order(
        client,
        order_id="12345",
        amount=2
    )
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def amend_order(
    client,
    order_id: str,
    amount: float = None,
    price: float = None,
    post_only: bool = None,
    advanced: str = None,
    stop_price: float = None,
) -> dict:
    """
    Изменение параметров существующего ордера.

    Args:
        client: Экземпляр DeribitClient
        order_id: ID ордера
        amount: Новый объём
        price: Новая цена
        post_only: Флаг post-only
        advanced: "usd" для расчёта в USD
        stop_price: Новая цена триггера

    Returns:
        dict с обновлёнными данными ордера

    Raises:
        ValueError: Если не указан ни один параметр для изменения
        Exception: При ошибке запроса к API
    """
    if all(v is None for v in [amount, price, post_only, advanced, stop_price]):
        raise ValueError(
            "Необходимо указать хотя бы один параметр для изменения: "
            "amount, price, post_only, advanced или stop_price"
        )

    params = {"order_id": order_id}

    if amount is not None:
        params["amount"] = amount
    if price is not None:
        params["price"] = price
    if post_only is not None:
        params["post_only"] = post_only
    if advanced is not None:
        params["advanced"] = advanced
    if stop_price is not None:
        params["stop_price"] = stop_price

    logger.info(
        f"Изменение ордера: {order_id} | "
        f"params={{amount={amount}, price={price}}}"
    )

    result = await client.call_private(
        method="private/edit",
        params=params
    )

    order_data = result.get("order", {})

    order = {
        "order_id": order_data.get("order_id"),
        "order_state": order_data.get("order_state"),
        "order_type": order_data.get("order_type"),
        "instrument_name": order_data.get("instrument_name"),
        "price": order_data.get("price"),
        "amount": order_data.get("amount"),
        "filled_amount": order_data.get("filled_amount"),
        "average_price": order_data.get("average_price"),
        "last_update_timestamp": order_data.get("last_update_timestamp"),
    }

    logger.info(
        f"Ордер изменён: {order['order_id']} | "
        f"new_price={order['price']} | new_amount={order['amount']}"
    )

    return order
