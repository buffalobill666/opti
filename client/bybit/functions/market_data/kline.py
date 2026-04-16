"""
Получение исторических данных свечей (OHLCV) для опционов Bybit.

API: GET /v5/market/kline
Документация: https://bybit-exchange.github.io/docs/v5/market/kline

Для опционов используется category="option".

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    symbol (str): Символ инструмента (напр. "BTC-27DEC24-80000-C")
    interval (str): Интервал свечи —
        "1", "3", "5", "15", "30",
        "60", "120", "240", "360", "720",
        "D", "W", "M"
    start_time (int, optional): Время начала (мс)
    end_time (int, optional): Время окончания (мс)
    limit (int): Лимит записей (макс 1000, по умолчанию 200)

Возвращает:
    list[dict]: Список свечей:
        - start_time (int): Время начала свечи (мс)
        - open (float): Цена открытия
        - high (float): Максимальная цена
        - low (float): Минимальная цена
        - close (float): Цена закрытия
        - volume (float): Объём
        - turnover (float): Оборот в валюте расчёта

Пример:
    klines = await get_kline(
        client,
        symbol="BTC-27DEC24-80000-C",
        interval="60",
        limit=100
    )
    for k in klines:
        print(f"O: {k['open']} H: {k['high']} L: {k['low']} C: {k['close']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_kline(
    client,
    symbol: str,
    interval: str = "60",
    start_time: int = None,
    end_time: int = None,
    limit: int = 200,
) -> list:
    """
    Получение свечных данных для опциона.

    Args:
        client: Экземпляр BybitClient
        symbol: Символ инструмента
        interval: Интервал свечи
        start_time: Время начала (мс)
        end_time: Время окончания (мс)
        limit: Лимит записей (макс 1000)

    Returns:
        list[dict] с данными свечей

    Raises:
        ValueError: Если interval невалиден или limit > 1000
        Exception: При ошибке запроса к API
    """
    valid_intervals = {
        "1", "3", "5", "15", "30",
        "60", "120", "240", "360", "720",
        "D", "W", "M",
    }
    if interval not in valid_intervals:
        raise ValueError(
            f"Неподдерживаемый интервал: {interval}. "
            f"Допустимые: {valid_intervals}"
        )
    if limit > 1000:
        raise ValueError(f"Максимальный лимит: 1000. Получено: {limit}")

    params = {
        "category": "option",
        "symbol": symbol,
        "interval": interval,
        "limit": str(limit),
    }

    if start_time:
        params["start"] = str(start_time)
    if end_time:
        params["end"] = str(end_time)

    logger.info(
        f"Запрос свечей: {symbol} | interval={interval} | limit={limit}"
    )

    result = await client.call_public(
        method="get_kline",
        params=params,
    )

    klines = []
    for item in result.get("list", []):
        klines.append({
            "start_time": int(item[0]),
            "open": float(item[1]),
            "high": float(item[2]),
            "low": float(item[3]),
            "close": float(item[4]),
            "volume": float(item[5]),
            "turnover": float(item[6]),
        })

    logger.info(
        f"Получено свечей: {len(klines)} | "
        f"symbol={symbol} | interval={interval}"
    )

    return klines
