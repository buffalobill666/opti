"""
Размещение ордера на покупку/продажу опциона Bybit.

API: POST /v5/order/create
Документация: https://bybit-exchange.github.io/docs/v5/order/create-order

Для опционов используется category="option".
Опционы Bybit требуют orderLinkId (обязательный, макс 36 символов).

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    symbol (str): Символ инструмента (напр. "BTC-27DEC24-80000-C")
    side (str): Направление — "Buy" или "Sell"
    order_type (str): Тип ордера — "Limit", "Market"
    qty (str): Количество контрактов
    price (str, optional): Цена для лимитного ордера
    order_link_id (str): Уникальный ID ордера (макс 36 символов, обязательный для опционов)
    time_in_force (str): Время действия — "GTC", "IOC", "FOK", "PostOnly"
    reduce_only (bool): Только уменьшение позиции
    close_on_trigger (bool): Закрытие позиции при триггере
    order_iv (str, optional): Подразумеваемая волатильность (приоритет над price)
    mmp (bool): Market Maker Protection
    take_profit (str, optional): Цена тейк-профита
    stop_loss (str, optional): Цена стоп-лосса
    tp_limit_price (str, optional): Лимитная цена TP
    sl_limit_price (str, optional): Лимитная цена SL
    tp_trigger_by (str, optional): Триггер TP — "LastPrice", "IndexPrice", "MarkPrice"
    sl_trigger_by (str, optional): Триггер SL — "LastPrice", "IndexPrice", "MarkPrice"

Возвращает:
    dict:
        - order_id (str): ID ордера
        - order_link_id (str): Пользовательский ID
        - symbol (str): Символ инструмента
        - side (str): Направление
        - order_type (str): Тип ордера
        - qty (str): Количество
        - price (str): Цена
        - time_in_force (str): Время действия
        - order_status (str): Состояние — "Created", "New", "Filled", "Cancelled", "Rejected"
        - created_time (str): Время создания (мс)
        - updated_time (str): Время обновления (мс)

Пример:
    # Лимитный ордер на покупку
    order = await create_order(
        client,
        symbol="BTC-27DEC24-80000-C",
        side="Buy",
        order_type="Limit",
        qty="1",
        price="1500",
        order_link_id="my_order_001",
        time_in_force="GTC"
    )
    print(f"Order {order['order_id']} created")
"""

import uuid

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def create_order(
    client,
    symbol: str,
    side: str,
    order_type: str,
    qty: str,
    price: str = None,
    order_link_id: str = None,
    time_in_force: str = "GTC",
    reduce_only: bool = False,
    close_on_trigger: bool = False,
    order_iv: str = None,
    mmp: bool = False,
    take_profit: str = None,
    stop_loss: str = None,
    tp_limit_price: str = None,
    sl_limit_price: str = None,
    tp_trigger_by: str = None,
    sl_trigger_by: str = None,
) -> dict:
    """
    Размещение ордера на покупку или продажу опциона.

    Args:
        client: Экземпляр BybitClient
        symbol: Символ инструмента
        side: "Buy" или "Sell"
        order_type: "Limit" или "Market"
        qty: Количество контрактов
        price: Цена (обязательна для Limit)
        order_link_id: Уникальный ID (генерируется если None)
        time_in_force: "GTC", "IOC", "FOK", "PostOnly"
        reduce_only: Только уменьшение позиции
        close_on_trigger: Закрытие при триггере
        order_iv: Подразумеваемая волатильность
        mmp: Market Maker Protection
        take_profit: Цена TP
        stop_loss: Цена SL
        tp_limit_price: Лимитная цена TP
        sl_limit_price: Лимитная цена SL
        tp_trigger_by: Триггер TP
        sl_trigger_by: Триггер SL

    Returns:
        dict с данными ордера

    Raises:
        ValueError: Если side или order_type невалидны
        Exception: При ошибке запроса к API
    """
    if side not in ("Buy", "Sell"):
        raise ValueError(f"Неподдерживаемая сторона: {side}. Используйте 'Buy' или 'Sell'")
    if order_type not in ("Limit", "Market"):
        raise ValueError(
            f"Неподдерживаемый тип: {order_type}. Используйте 'Limit' или 'Market'"
        )
    if order_type == "Limit" and price is None and order_iv is None:
        raise ValueError("Для лимитного ордера нужен price или order_iv")

    # Генерация orderLinkId если не указан
    if order_link_id is None:
        order_link_id = f"or_{uuid.uuid4().hex[:20]}"

    params = {
        "category": "option",
        "symbol": symbol,
        "side": side,
        "orderType": order_type,
        "qty": qty,
        "orderLinkId": order_link_id,
        "timeInForce": time_in_force,
        "reduceOnly": reduce_only,
        "closeOnTrigger": close_on_trigger,
        "mmp": mmp,
    }

    if price is not None:
        params["price"] = price
    if order_iv is not None:
        params["orderIv"] = order_iv
    if take_profit is not None:
        params["takeProfit"] = take_profit
    if stop_loss is not None:
        params["stopLoss"] = stop_loss
    if tp_limit_price is not None:
        params["tpLimitPrice"] = tp_limit_price
    if sl_limit_price is not None:
        params["slLimitPrice"] = sl_limit_price
    if tp_trigger_by is not None:
        params["tpTriggerBy"] = tp_trigger_by
    if sl_trigger_by is not None:
        params["slTriggerBy"] = sl_trigger_by

    logger.info(
        f"Создание ордера: {side} {symbol} | "
        f"type={order_type} | qty={qty} | price={price or 'MARKET'} | "
        f"linkId={order_link_id}"
    )

    result = await client.call_private(
        method="place_order",
        params=params,
    )

    order = {
        "order_id": result.get("orderId"),
        "order_link_id": result.get("orderLinkId"),
        "symbol": result.get("symbol"),
        "side": result.get("side"),
        "order_type": result.get("orderType"),
        "qty": result.get("qty"),
        "price": result.get("price"),
        "time_in_force": result.get("timeInForce"),
        "order_status": result.get("orderStatus"),
        "created_time": result.get("createdTime"),
        "updated_time": result.get("updatedTime"),
    }

    logger.info(
        f"Ордер создан: {order['order_id']} | "
        f"status={order['order_status']} | "
        f"linkId={order['order_link_id']}"
    )

    return order
