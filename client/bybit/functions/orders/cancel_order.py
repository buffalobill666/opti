"""
Отмена ордера Bybit.

API: POST /v5/order/cancel
Документация: https://bybit-exchange.github.io/docs/v5/order/cancel

Для опционов используется category="option".

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    symbol (str): Символ инструмента
    order_id (str, optional): ID ордера (один из order_id или order_link_id)
    order_link_id (str, optional): Пользовательский ID ордера

Возвращает:
    dict:
        - order_id (str): ID ордера
        - order_link_id (str): Пользовательский ID
        - symbol (str): Символ инструмента

Пример:
    result = await cancel_order(
        client,
        symbol="BTC-27DEC24-80000-C",
        order_id="abc123"
    )
    print(f"Order {result['order_id']} cancelled")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def cancel_order(
    client,
    symbol: str,
    order_id: str = None,
    order_link_id: str = None,
) -> dict:
    """
    Отмена активного ордера.

    Args:
        client: Экземпляр BybitClient
        symbol: Символ инструмента
        order_id: ID ордера
        order_link_id: Пользовательский ID

    Returns:
        dict с данными отменённого ордера

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

    logger.info(
        f"Отмена ордера: {symbol} | "
        f"orderId={order_id or order_link_id}"
    )

    result = await client.call_private(
        method="cancel_order",
        params=params,
    )

    order = {
        "order_id": result.get("orderId"),
        "order_link_id": result.get("orderLinkId"),
        "symbol": result.get("symbol"),
    }

    logger.info(
        f"Ордер отменён: {order['order_id']} | "
        f"linkId={order['order_link_id']}"
    )

    return order
