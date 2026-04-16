"""
Получение ставки финансирования для опционов Bybit.

API: GET /v5/market/funding/history
Документация: https://bybit-exchange.github.io/docs/v5/market/funding

Для опционов используется category="option".

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    symbol (str): Символ инструмента
    limit (int): Лимит записей (макс 200, по умолчанию 20)

Возвращает:
    list[dict]: Список ставок финансирования:
        - symbol (str): Символ инструмента
        - funding_rate (float): Ставка финансирования
        - funding_rate_timestamp (int): Время расчёта (мс)

Пример:
    rates = await get_funding_rate(client, symbol="BTC-27DEC24-80000-C")
    for r in rates:
        print(f"{r['symbol']} | Rate: {r['funding_rate']} | Time: {r['funding_rate_timestamp']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_funding_rate(
    client,
    symbol: str,
    limit: int = 20,
) -> list:
    """
    Получение истории ставок финансирования.

    Args:
        client: Экземпляр BybitClient
        symbol: Символ инструмента
        limit: Лимит записей (макс 200)

    Returns:
        list[dict] с данными ставок

    Raises:
        ValueError: Если limit > 200
        Exception: При ошибке запроса к API
    """
    if limit > 200:
        raise ValueError(f"Максимальный лимит: 200. Получено: {limit}")

    params = {
        "category": "option",
        "symbol": symbol,
        "limit": str(limit),
    }

    logger.info(f"Запрос ставок финансирования: {symbol}")

    result = await client.call_public(
        method="get_funding_rate_history",
        params=params,
    )

    rates = []
    for item in result.get("list", []):
        rates.append({
            "symbol": item.get("symbol"),
            "funding_rate": float(item.get("fundingRate", 0)),
            "funding_rate_timestamp": int(item.get("fundingRateTimestamp", 0)),
        })

    logger.info(f"Получено ставок финансирования: {len(rates)}")

    return rates
