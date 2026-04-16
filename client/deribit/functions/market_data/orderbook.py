"""
Получение стакана заявок (order book) для опциона.

API: public/get_order_book
Документация: https://docs.deribit.com/api-reference/market-data/public-get_order_book

Параметры:
    client (DeribitClient): Экземпляр Deribit клиента
    instrument_name (str): Название инструмента (напр. "BTC-27DEC24-80000-C")
    depth (int): Количество уровней стакана — 1, 5, 10, 20, 50, 100, 1000, 10000

Возвращает:
    dict:
        - instrument_name (str): Название инструмента
        - timestamp (int): Временная метка (мс)
        - state (str): Состояние книги — "open", "settlement", "delivered", "inactive"
        - bids (list[list[float]]): Массив [[цена, объём], ...] — заявки на покупку
        - asks (list[list[float]]): Массив [[цена, объём], ...] — заявки на продажу
        - best_bid_price (float): Лучшая цена покупки
        - best_bid_amount (float): Объём лучшей заявки покупки
        - best_ask_price (float): Лучшая цена продажи
        - best_ask_amount (float): Объём лучшей заявки продажи
        - mark_price (float): Mark price
        - index_price (float): Индексная цена
        - underlying_price (float): Цена базового актива (только для опционов)
        - last_price (float): Цена последней сделки
        - open_interest (float): Объём открытых позиций
        - greeks (dict): Греки опциона:
            - delta (float)
            - gamma (float)
            - rho (float)
            - theta (float)
            - vega (float)
        - bid_iv (float): Подразумеваемая волатильность bid
        - ask_iv (float): Подразумеваемая волатильность ask
        - mark_iv (float): Подразумеваемая волатильность mark

Пример:
    ob = await get_orderbook(client, "BTC-27DEC24-80000-C", depth=10)
    print(f"Best bid: {ob['best_bid_price']} | Best ask: {ob['best_ask_price']}")
    print(f"Mark IV: {ob['mark_iv']}% | Delta: {ob['greeks']['delta']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_orderbook(client, instrument_name: str, depth: int = 10) -> dict:
    """
    Получение стакана заявок для указанного опциона.

    Args:
        client: Экземпляр DeribitClient
        instrument_name: Название инструмента
        depth: Количество уровней (1, 5, 10, 20, 50, 100, 1000, 10000)

    Returns:
        dict с данными стакана и греками опциона

    Raises:
        ValueError: Если depth невалиден
        Exception: При ошибке запроса к API
    """
    valid_depths = [1, 5, 10, 20, 50, 100, 1000, 10000]
    if depth not in valid_depths:
        raise ValueError(
            f"Неподдерживаемая глубина: {depth}. "
            f"Допустимые: {valid_depths}"
        )

    logger.info(f"Запрос стакана: {instrument_name} | depth={depth}")

    result = await client.call_public(
        method="public/get_order_book",
        params={
            "instrument_name": instrument_name,
            "depth": depth,
        }
    )

    greeks = result.get("greeks", {})

    orderbook = {
        "instrument_name": result.get("instrument_name"),
        "timestamp": result.get("timestamp"),
        "state": result.get("state"),
        "bids": result.get("bids", []),
        "asks": result.get("asks", []),
        "best_bid_price": result.get("best_bid_price"),
        "best_bid_amount": result.get("best_bid_amount"),
        "best_ask_price": result.get("best_ask_price"),
        "best_ask_amount": result.get("best_ask_amount"),
        "mark_price": result.get("mark_price"),
        "index_price": result.get("index_price"),
        "underlying_price": result.get("underlying_price"),
        "last_price": result.get("last_price"),
        "open_interest": result.get("open_interest"),
        "greeks": {
            "delta": greeks.get("delta"),
            "gamma": greeks.get("gamma"),
            "rho": greeks.get("rho"),
            "theta": greeks.get("theta"),
            "vega": greeks.get("vega"),
        },
        "bid_iv": result.get("bid_iv"),
        "ask_iv": result.get("ask_iv"),
        "mark_iv": result.get("mark_iv"),
    }

    logger.info(
        f"Стакан: {instrument_name} | "
        f"bid={orderbook['best_bid_price']} ask={orderbook['best_ask_price']} | "
        f"mark_iv={orderbook['mark_iv']}%"
    )

    return orderbook
