"""
Изменение существующего ордера Bybit.

API: POST /v5/order/amend
Документация: https://bybit-exchange.github.io/docs/v5/order/amend-order

Для опционов используется category="option".
Можно изменить: цену, количество, подразумеваемую волатильность.

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    symbol (str): Символ инструмента
    order_id (str, optional): ID ордера (один из order_id или order_link_id)
    order_link_id (str, optional): Пользовательский ID ордера
    price (str, optional): Новая цена
    qty (str, optional): Новое количество
    order_iv (str, optional): Новая подразумеваемая волатильность
    time_in_force (str, optional): Новое время действия
    take_profit (str, optional): Новая цена TP
    stop_loss (str, optional): Новая цена SL
    tp_limit_price (str, optional): Новая лимитная цена TP
    sl_limit_price (str, optional): Новая лимитная цена SL
    tp_trigger_by (str, optional): Новый триггер TP
    sl_trigger_by (str, optional): Новый триггер SL

Возвращает:
    dict:
        - order_id (str): ID ордера
        - order_link_id (str): Пользовательский ID
        - symbol (str): Символ инструмента
        - side (str): Направление
        - qty (str): Новое количество
        - price (str): Новая цена
        - order_status (str): Состояние
        - updated_time (str): Время обновления (мс)

Пример:
    # Изменить цену
    updated = await amend_order(
        client,
        symbol="BTC-27DEC24-80000-C",
        order_id="abc123",
        price="1600"
    )
    print(f"Order {updated['order_id']} updated, new price: {updated['price']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def amend_order(
    client,
    symbol: str,
    order_id: str = None,
    order_link_id: str = None,
    price: str = None,
    qty: str = None,
    order_iv: str = None,
    time_in_force: str = None,
    take_profit: str = None,
    stop_loss: str = None,
    tp_limit_price: str = None,
    sl_limit_price: str = None,
    tp_trigger_by: str = None,
    sl_trigger_by: str = None,
) -> dict:
    """
    Изменение параметров существующего ордера.

    Args:
        client: Экземпляр BybitClient
        symbol: Символ инструмента
        order_id: ID ордера
        order_link_id: Пользовательский ID
        price: Новая цена
        qty: Новое количество
        order_iv: Новая подразумеваемая волатильность
        time_in_force: Новое время действия
        take_profit: Новая цена TP
        stop_loss: Новая цена SL
        tp_limit_price: Новая лимитная цена TP
        sl_limit_price: Новая лимитная цена SL
        tp_trigger_by: Новый триггер TP
        sl_trigger_by: Новый триггер SL

    Returns:
        dict с обновлёнными данными ордера

    Raises:
        ValueError: Если не указан ни order_id, ни order_link_id
        Exception: При ошибке запроса к API
    """
    if not order_id and not order_link_id:
        raise ValueError("Необходимо указать order_id или order_link_id")

    params = {
        "category": "option",
        "symbol": symbol,
    }

    if order_id:
        params["orderId"] = order_id
    if order_link_id:
        params["orderLinkId"] = order_link_id
    if price is not None:
        params["price"] = price
    if qty is not None:
        params["qty"] = qty
    if order_iv is not None:
        params["orderIv"] = order_iv
    if time_in_force is not None:
        params["timeInForce"] = time_in_force
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
        f"Изменение ордера: {symbol} | "
        f"orderId={order_id or order_link_id} | "
        f"params={{price={price}, qty={qty}}}"
    )

    result = await client.call_private(
        method="amend_order",
        params=params,
    )

    order = {
        "order_id": result.get("orderId"),
        "order_link_id": result.get("orderLinkId"),
        "symbol": result.get("symbol"),
        "side": result.get("side"),
        "qty": result.get("qty"),
        "price": result.get("price"),
        "order_status": result.get("orderStatus"),
        "updated_time": result.get("updatedTime"),
    }

    logger.info(
        f"Ордер изменён: {order['order_id']} | "
        f"new_price={order['price']} | new_qty={order['qty']}"
    )

    return order
