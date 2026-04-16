"""
Размещение ордера на покупку/продажу опциона Deribit.

API: private/buy (для покупки) или private/sell (для продажи)
Документация: https://docs.deribit.com/api-reference/trading/private-buy

Параметры:
    client (DeribitClient): Экземпляр Deribit клиента
    instrument_name (str): Название инструмента (напр. "BTC-27DEC24-80000-C")
    side (str): Направление — "buy" или "sell"
    amount (float): Количество контрактов
    type (str): Тип ордера — "limit", "market", "stop_limit", "stop",
                "take_limit", "take_market", "stop_market",
                "trailing_stop", "advanced_usd"
    price (float, optional): Цена для лимитного ордера
    time_in_force (str): Время действия — "good_til_cancelled" (GTC),
                         "fill_or_kill" (FOK), "immediate_or_cancel" (IOC)
    reduce_only (bool): Только уменьшение позиции (по умолчанию False)
    post_only (bool): Только пост-ордер, не удаляющий ликвидность (по умолчанию True)
    label (str, optional): Метка ордера для идентификации
    advanced (str, optional): "usd" для расчёта цены в USD вместо контрактов
    trigger_price (float, optional): Цена триггера для стоп-ордеров
    trigger_offset (float, optional): Смещение триггера для trailing stop
    trigger (str, optional): Тип триггера — "index_price", "mark_price", "last_price"
    mmp (bool): Market Maker Protection (по умолчанию False)

Возвращает:
    dict:
        - order_id (str): ID ордера
        - order_state (str): Состояние — "open", "filled", "rejected", "cancelled"
        - order_type (str): Тип ордера
        - instrument_name (str): Название инструмента
        - direction (str): Направление — "buy" или "sell"
        - price (float): Цена ордера
        - amount (float): Запрошенный объём
        - filled_amount (float): Заполненный объём
        - average_price (float): Средняя цена заполнения
        - remaining_amount (float): Оставшийся объём
        - commission (float): Комиссия
        - creation_timestamp (int): Время создания (мс)
        - last_update_timestamp (int): Время последнего обновления (мс)
        - trades (list[dict]): Список сделок (если ордер частично/полностью заполнен)

Пример:
    # Лимитный ордер на покупку
    order = await create_order(
        client,
        instrument_name="BTC-27DEC24-80000-C",
        side="buy",
        amount=1,
        type="limit",
        price=1500,
        time_in_force="good_til_cancelled"
    )
    print(f"Order {order['order_id']} created, state: {order['order_state']}")

    # Рыночный ордер на продажу
    order = await create_order(
        client,
        instrument_name="BTC-27DEC24-80000-C",
        side="sell",
        amount=1,
        type="market"
    )
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def create_order(
    client,
    instrument_name: str,
    side: str,
    amount: float,
    type: str = "limit",
    price: float = None,
    time_in_force: str = "good_til_cancelled",
    reduce_only: bool = False,
    post_only: bool = True,
    label: str = None,
    advanced: str = None,
    trigger_price: float = None,
    trigger_offset: float = None,
    trigger: str = None,
    mmp: bool = False,
) -> dict:
    """
    Размещение ордера на покупку или продажу опциона.

    Args:
        client: Экземпляр DeribitClient
        instrument_name: Название инструмента
        side: "buy" или "sell"
        amount: Количество контрактов
        type: Тип ордера
        price: Цена (обязательна для limit ордеров)
        time_in_force: Время действия ордера
        reduce_only: Только уменьшение позиции
        post_only: Только пост-ордер
        label: Метка ордера
        advanced: "usd" для расчёта в USD
        trigger_price: Цена триггера
        trigger_offset: Смещение триггера
        trigger: Тип триггера
        mmp: Market Maker Protection

    Returns:
        dict с данными ордера

    Raises:
        ValueError: Если side или type невалидны
        Exception: При ошибке запроса к API
    """
    if side not in ("buy", "sell"):
        raise ValueError(f"Неподдерживаемая сторона: {side}. Используйте 'buy' или 'sell'")

    valid_types = [
        "limit", "market", "stop_limit", "stop",
        "take_limit", "take_market", "stop_market",
        "trailing_stop", "advanced_usd"
    ]
    if type not in valid_types:
        raise ValueError(
            f"Неподдерживаемый тип ордера: {type}. "
            f"Допустимые: {valid_types}"
        )

    if type == "limit" and price is None:
        raise ValueError("Для лимитного ордера необходимо указать price")

    # Выбираем метод API в зависимости от стороны
    method = "private/buy" if side == "buy" else "private/sell"

    params = {
        "instrument_name": instrument_name,
        "amount": amount,
        "type": type,
        "time_in_force": time_in_force,
        "reduce_only": reduce_only,
        "post_only": post_only,
        "mmp": mmp,
    }

    if price is not None:
        params["price"] = price
    if label is not None:
        params["label"] = label
    if advanced is not None:
        params["advanced"] = advanced
    if trigger_price is not None:
        params["trigger_price"] = trigger_price
    if trigger_offset is not None:
        params["trigger_offset"] = trigger_offset
    if trigger is not None:
        params["trigger"] = trigger

    logger.info(
        f"Создание ордера: {side.upper()} {instrument_name} | "
        f"type={type} | amount={amount} | price={price}"
    )

    result = await client.call_private(method=method, params=params)

    order_data = result.get("order", {})
    trades = result.get("trades", [])

    order = {
        "order_id": order_data.get("order_id"),
        "order_state": order_data.get("order_state"),
        "order_type": order_data.get("order_type"),
        "instrument_name": order_data.get("instrument_name"),
        "direction": order_data.get("direction"),
        "price": order_data.get("price"),
        "amount": order_data.get("amount"),
        "filled_amount": order_data.get("filled_amount"),
        "average_price": order_data.get("average_price"),
        "remaining_amount": order_data.get("amount", 0) - order_data.get("filled_amount", 0),
        "commission": order_data.get("commission"),
        "creation_timestamp": order_data.get("creation_timestamp"),
        "last_update_timestamp": order_data.get("last_update_timestamp"),
        "trades": trades,
    }

    logger.info(
        f"Ордер создан: {order['order_id']} | "
        f"state={order['order_state']} | "
        f"filled={order['filled_amount']}/{order['amount']}"
    )

    return order
