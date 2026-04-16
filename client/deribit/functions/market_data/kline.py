"""
Получение исторических данных свечей (OHLCV) для опционов.

API: public/get_tradingview_chart_data
Документация: https://docs.deribit.com/api-reference/market-data/public-get_tradingview_chart_data

Параметры:
    client (DeribitClient): Экземпляр Deribit клиента
    instrument_name (str): Название инструмента (напр. "BTC-27DEC24-80000-C")
    start_timestamp (int): Время начала в миллисекундах (Unix epoch)
    end_timestamp (int): Время окончания в миллисекундах (Unix epoch)
    resolution (str): Интервал свечи — "1", "3", "5", "10", "15", "30",
                      "60", "120", "180", "240", "1D", "7D", "14D", "21D", "1M"

Возвращает:
    dict:
        - ticks (list[int]): Массив временных меток (мс)
        - open (list[float]): Цены открытия
        - high (list[float]): Максимальные цены
        - low (list[float]): Минимальные цены
        - close (list[float]): Цены закрытия
        - volume (list[float]): Объёмы
        - cost (list[float]): Стоимость в базовой валюте

Пример:
    data = await get_kline(
        client,
        instrument_name="BTC-27DEC24-80000-C",
        start_timestamp=1700000000000,
        end_timestamp=1700100000000,
        resolution="60"
    )
    for i in range(len(data['ticks'])):
        print(f"O: {data['open'][i]} H: {data['high'][i]} L: {data['low'][i]} C: {data['close'][i]}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_kline(
    client,
    instrument_name: str,
    start_timestamp: int,
    end_timestamp: int,
    resolution: str = "60"
) -> dict:
    """
    Получение свечных данных для графика TradingView.

    Args:
        client: Экземпляр DeribitClient
        instrument_name: Название инструмента
        start_timestamp: Время начала (мс)
        end_timestamp: Время окончания (мс)
        resolution: Интервал свечи

    Returns:
        dict с массивами ticks, open, high, low, close, volume, cost

    Raises:
        ValueError: Если resolution невалиден
        Exception: При ошибке запроса к API
    """
    valid_resolutions = [
        "1", "3", "5", "10", "15", "30",
        "60", "120", "180", "240",
        "1D", "7D", "14D", "21D", "1M"
    ]
    if resolution not in valid_resolutions:
        raise ValueError(
            f"Неподдерживаемый интервал: {resolution}. "
            f"Допустимые: {valid_resolutions}"
        )

    logger.info(
        f"Запрос свечей: {instrument_name} | "
        f"resolution={resolution} | "
        f"period={start_timestamp} - {end_timestamp}"
    )

    result = await client.call_public(
        method="public/get_tradingview_chart_data",
        params={
            "instrument_name": instrument_name,
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "resolution": resolution,
        }
    )

    kline_data = {
        "ticks": result.get("ticks", []),
        "open": result.get("open", []),
        "high": result.get("high", []),
        "low": result.get("low", []),
        "close": result.get("close", []),
        "volume": result.get("volume", []),
        "cost": result.get("cost", []),
    }

    logger.info(
        f"Получено свечей: {len(kline_data['ticks'])} ({instrument_name}, {resolution})"
    )

    return kline_data
