"""
Получение последних сделок для опционов Bybit.

API: GET /v5/market/recent-trade
Документация: https://bybit-exchange.github.io/docs/v5/market/recent-trade

Для опционов используется category="option".

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    symbol (str): Символ инструмента
    limit (int): Лимит записей (макс 1000, по умолчанию 50)

Возвращает:
    list[dict]: Список последних сделок:
        - exec_id (str): ID исполнения
        - symbol (str): Символ инструмента
        - price (float): Цена сделки
        - size (float): Размер сделки
        - side (str): Направление — "Buy" или "Sell"
        - time (str): Время сделки (мс)
        - is_block_trade (bool): Флаг блочной сделки

Пример:
    trades = await get_recent_trades(client, symbol="BTC-27DEC24-80000-C", limit=10)
    for t in trades:
        print(f"{t['side']} {t['size']} @ {t['price']} | {t['time']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_recent_trades(
    client,
    symbol: str,
    limit: int = 50,
) -> list:
    """
    Получение последних сделок по опциону.

    Args:
        client: Экземпляр BybitClient
        symbol: Символ инструмента
        limit: Лимит записей (макс 1000)

    Returns:
        list[dict] с данными сделок

    Raises:
        ValueError: Если limit > 1000
        Exception: При ошибке запроса к API
    """
    if limit > 1000:
        raise ValueError(f"Максимальный лимит: 1000. Получено: {limit}")

    params = {
        "category": "option",
        "symbol": symbol,
        "limit": str(limit),
    }

    logger.info(f"Запрос последних сделок: {symbol}")

    result = await client.call_public(
        method="get_public_trade_history",
        params=params,
    )

    trades = []
    for item in result.get("list", []):
        trades.append({
            "exec_id": item.get("execId"),
            "symbol": item.get("symbol"),
            "price": float(item.get("price", 0)),
            "size": float(item.get("size", 0)),
            "side": item.get("side"),
            "time": item.get("time"),
            "is_block_trade": item.get("isBlockTrade", False),
        })

    logger.info(f"Получено сделок: {len(trades)}")

    return trades
