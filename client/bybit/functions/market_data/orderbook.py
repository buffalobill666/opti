"""
Получение стакана заявок (order book) для опционов Bybit.

API: GET /v5/market/orderbook
Документация: https://bybit-exchange.github.io/docs/v5/market/orderbook

Для опционов используется category="option".

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    symbol (str): Символ инструмента (напр. "BTC-27DEC24-80000-C")
    limit (int): Количество уровней — 1, 5, 10, 25, 50, 100, 200, 500

Возвращает:
    dict:
        - symbol (str): Символ инструмента
        - bids (list[list[float]]): Массив [[цена, объём], ...] — заявки на покупку
        - asks (list[list[float]]): Массив [[цена, объём], ...] — заявки на продажу
        - timestamp (int): Временная метка (мс)
        - update_id (int): ID обновления

Пример:
    ob = await get_orderbook(client, symbol="BTC-27DEC24-80000-C", limit=10)
    print(f"Bids: {ob['bids'][:3]}")
    print(f"Asks: {ob['asks'][:3]}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_orderbook(client, symbol: str, limit: int = 25) -> dict:
    """
    Получение стакана заявок для опциона.

    Args:
        client: Экземпляр BybitClient
        symbol: Символ инструмента
        limit: Количество уровней (1, 5, 10, 25, 50, 100, 200, 500)

    Returns:
        dict с данными стакана

    Raises:
        ValueError: Если limit невалиден
        Exception: При ошибке запроса к API
    """
    valid_limits = {1, 5, 10, 25, 50, 100, 200, 500}
    if limit not in valid_limits:
        raise ValueError(
            f"Неподдерживаемый лимит: {limit}. "
            f"Допустимые: {valid_limits}"
        )

    params = {
        "category": "option",
        "symbol": symbol,
        "limit": str(limit),
    }

    logger.info(f"Запрос стакана: {symbol} | limit={limit}")

    result = await client.call_public(
        method="get_orderbook",
        params=params,
    )

    bids = []
    for bid in result.get("b", []):
        bids.append([float(bid[0]), float(bid[1])])

    asks = []
    for ask in result.get("a", []):
        asks.append([float(ask[0]), float(ask[1])])

    orderbook = {
        "symbol": result.get("s"),
        "bids": bids,
        "asks": asks,
        "timestamp": int(result["ts"]) if result.get("ts") else None,
        "update_id": int(result.get("u", 0)),
    }

    logger.info(
        f"Стакан: {orderbook['symbol']} | "
        f"bids={len(bids)} asks={len(asks)} | "
        f"best_bid={bids[0][0] if bids else 'N/A'} "
        f"best_ask={asks[0][0] if asks else 'N/A'}"
    )

    return orderbook
