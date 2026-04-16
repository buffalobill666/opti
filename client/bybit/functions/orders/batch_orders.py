"""
Пакетное размещение ордеров на Bybit.

API: POST /v5/order/create-batch
Документация: https://bybit-exchange.github.io/docs/v5/order/batch-place

Для опционов используется category="option".
Максимум 20 ордеров за один запрос.

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    orders (list[dict]): Список ордеров, каждый с полями:
        - symbol (str): Символ инструмента
        - side (str): "Buy" или "Sell"
        - order_type (str): "Limit" или "Market"
        - qty (str): Количество
        - price (str, optional): Цена
        - order_link_id (str, optional): Пользовательский ID
        - time_in_force (str): "GTC", "IOC", "FOK", "PostOnly"

Возвращает:
    dict:
        - result (list[dict]): Результаты по каждому ордеру
        - failed (list[dict]): Неудачные ордера с ошибками

Пример:
    orders = [
        {"symbol": "BTC-27DEC24-80000-C", "side": "Buy", "order_type": "Limit", "qty": "1", "price": "1500"},
        {"symbol": "BTC-27DEC24-90000-C", "side": "Buy", "order_type": "Limit", "qty": "1", "price": "1000"},
    ]
    result = await create_batch_order(client, orders)
    print(f"Успешно: {len(result['result'])}, Ошибки: {len(result['failed'])}")
"""

import uuid

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def create_batch_order(
    client,
    orders: list[dict],
) -> dict:
    """
    Пакетное размещение до 20 ордеров.

    Args:
        client: Экземпляр BybitClient
        orders: Список ордеров

    Returns:
        dict с результатами

    Raises:
        ValueError: Если orders > 20
        Exception: При ошибке запроса к API
    """
    if len(orders) > 20:
        raise ValueError(f"Максимум 20 ордеров за запрос. Получено: {len(orders)}")

    # Добавляем orderLinkId если не указан
    for order in orders:
        if "order_link_id" not in order:
            order["order_link_id"] = f"batch_{uuid.uuid4().hex[:16]}"

    # Формируем запрос
    request_orders = []
    for o in orders:
        req = {
            "category": "option",
            "symbol": o["symbol"],
            "side": o["side"],
            "orderType": o["order_type"],
            "qty": o["qty"],
            "orderLinkId": o["order_link_id"],
            "timeInForce": o.get("time_in_force", "GTC"),
        }
        if o.get("price"):
            req["price"] = o["price"]
        request_orders.append(req)

    logger.info(f"Пакетное размещение ордеров: {len(request_orders)} шт")

    result = await client.call_private(
        method="create_batch_order",
        params={"request": request_orders},
    )

    batch_result = {
        "result": result.get("result", []),
        "failed": result.get("failed", []),
    }

    logger.info(
        f"Пакетное размещение завершено: "
        f"успешно={len(batch_result['result'])}, "
        f"ошибки={len(batch_result['failed'])}"
    )

    return batch_result
