"""
Получение истории ордеров Bybit.

API: GET /v5/order/history
Документация: https://bybit-exchange.github.io/docs/v5/order/history

Для опционов используется category="option".
Поддерживается запрос закрытых позиций за последние 6 месяцев.

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    symbol (str, optional): Символ инструмента
    base_coin (str, optional): Базовая валюта — "BTC" или "ETH"
    order_id (str, optional): ID ордера
    order_link_id (str, optional): Пользовательский ID
    order_status (str, optional): Фильтр по статусу —
        "Created", "New", "Rejected", "PartiallyFilled",
        "PartiallyFilledCanceled", "Filled", "Cancelled", "Deactivated"
    order_filter (str, optional): Фильтр — "order", "tpslOrder", "StopOrder"
    limit (int): Лимит записей (макс 1000, по умолчанию 20)
    cursor (str, optional): Курсор для пагинации

Возвращает:
    dict:
        - orders (list[dict]): Список ордеров:
            - order_id (str): ID ордера
            - order_link_id (str): Пользовательский ID
            - symbol (str): Символ инструмента
            - side (str): Направление
            - order_type (str): Тип ордера
            - price (str): Цена
            - qty (str): Количество
            - filled_qty (str): Заполненное количество
            - avg_price (str): Средняя цена
            - order_status (str): Состояние
            - time_in_force (str): Время действия
            - created_time (str): Время создания
            - updated_time (str): Время обновления
        - next_page_cursor (str): Курсор для пагинации

Пример:
    result = await get_order_history(client, base_coin="BTC", limit=50)
    for order in result['orders']:
        print(f"{order['order_id']} | {order['symbol']} | "
              f"{order['order_status']} | avg_price={order['avg_price']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_order_history(
    client,
    symbol: str = None,
    base_coin: str = None,
    order_id: str = None,
    order_link_id: str = None,
    order_status: str = None,
    order_filter: str = None,
    limit: int = 20,
    cursor: str = None,
) -> dict:
    """
    Получение истории ордеров.

    Args:
        client: Экземпляр BybitClient
        symbol: Символ инструмента
        base_coin: "BTC" или "ETH"
        order_id: ID ордера
        order_link_id: Пользовательский ID
        order_status: Фильтр по статусу
        order_filter: Фильтр типа ордера
        limit: Лимит записей (макс 1000)
        cursor: Курсор для пагинации

    Returns:
        dict с данными ордеров

    Raises:
        ValueError: Если limit > 1000
        Exception: При ошибке запроса к API
    """
    if limit > 1000:
        raise ValueError(f"Максимальный лимит: 1000. Получено: {limit}")

    params = {
        "category": "option",
        "limit": str(limit),
    }

    if symbol:
        params["symbol"] = symbol
    if base_coin:
        params["baseCoin"] = base_coin
    if order_id:
        params["orderId"] = order_id
    if order_link_id:
        params["orderLinkId"] = order_link_id
    if order_status:
        params["orderStatus"] = order_status
    if order_filter:
        params["orderFilter"] = order_filter
    if cursor:
        params["cursor"] = cursor

    logger.info(
        f"Запрос истории ордеров: category=option | "
        f"baseCoin={base_coin or 'ALL'} | limit={limit}"
    )

    result = await client.call_private(
        method="get_order_history",
        params=params,
    )

    orders = []
    for item in result.get("list", []):
        orders.append({
            "order_id": item.get("orderId"),
            "order_link_id": item.get("orderLinkId"),
            "symbol": item.get("symbol"),
            "side": item.get("side"),
            "order_type": item.get("orderType"),
            "price": item.get("price"),
            "qty": item.get("qty"),
            "filled_qty": item.get("cumExecQty"),
            "avg_price": item.get("avgPrice"),
            "order_status": item.get("orderStatus"),
            "time_in_force": item.get("timeInForce"),
            "created_time": item.get("createdTime"),
            "updated_time": item.get("updatedTime"),
        })

    logger.info(
        f"Получено ордеров: {len(orders)} | "
        f"cursor={result.get('nextPageCursor')}"
    )

    return {
        "orders": orders,
        "next_page_cursor": result.get("nextPageCursor"),
    }
