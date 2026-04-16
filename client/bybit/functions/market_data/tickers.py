"""
Получение последних котировок (тикеров) для опционов Bybit.

API: GET /v5/market/tickers
Документация: https://bybit-exchange.github.io/docs/v5/market/tickers

Для опционов используется category="option".

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    base_coin (str, optional): Базовая валюта — "BTC" или "ETH"
    symbol (str, optional): Конкретный символ (напр. "BTC-27DEC24-80000-C")

Возвращает:
    list[dict]: Список тикеров:
        - symbol (str): Символ инструмента
        - bid_price (float): Лучшая цена покупки
        - bid_size (float): Объём лучшей покупки
        - bid_iv (float): Подразумеваемая волатильность bid
        - ask_price (float): Лучшая цена продажи
        - ask_size (float): Объём лучшей продажи
        - ask_iv (float): Подразумеваемая волатильность ask
        - last_price (float): Цена последней сделки
        - high_price_24h (float): Максимальная цена за 24ч
        - low_price_24h (float): Минимальная цена за 24ч
        - volume_24h (float): Объём за 24ч
        - turnover_24h (float): Оборот за 24ч
        - mark_price (float): Mark price
        - index_price (float): Индексная цена
        - mark_iv (float): Подразумеваемая волатильность mark
        - delta (float): Дельта
        - gamma (float): Гамма
        - vega (float): Вега
        - theta (float): Тета
        - predicted_delivery_price (float): Прогнозируемая цена доставки
        - change_24h (float): Изменение за 24ч в %

Пример:
    tickers = await get_tickers(client, base_coin="BTC")
    for t in tickers:
        print(f"{t['symbol']} | Mark: {t['mark_price']} | IV: {t['mark_iv']}%")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_tickers(
    client,
    base_coin: str = None,
    symbol: str = None,
) -> list:
    """
    Получение тикеров для опционов.

    Args:
        client: Экземпляр BybitClient
        base_coin: "BTC" или "ETH" (опционально)
        symbol: Конкретный символ (опционально)

    Returns:
        list[dict] с данными тикеров

    Raises:
        ValueError: Если base_coin невалидна
        Exception: При ошибке запроса к API
    """
    if base_coin and base_coin not in ("BTC", "ETH"):
        raise ValueError(
            f"Неподдерживаемая базовая валюта: {base_coin}. "
            f"Используйте 'BTC' или 'ETH'"
        )

    params = {"category": "option"}

    if base_coin:
        params["baseCoin"] = base_coin
    if symbol:
        params["symbol"] = symbol

    logger.info(
        f"Запрос тикеров: category=option, baseCoin={base_coin or 'ALL'}"
    )

    result = await client.call_public(
        method="get_tickers",
        params=params,
    )

    tickers = []
    for item in result.get("list", []):
        tickers.append({
            "symbol": item.get("symbol"),
            "bid_price": float(item.get("bid1Price", 0)),
            "bid_size": float(item.get("bid1Size", 0)),
            "bid_iv": float(item.get("bid1Iv", 0)),
            "ask_price": float(item.get("ask1Price", 0)),
            "ask_size": float(item.get("ask1Size", 0)),
            "ask_iv": float(item.get("ask1Iv", 0)),
            "last_price": float(item.get("lastPrice", 0)),
            "high_price_24h": float(item.get("highPrice24h", 0)),
            "low_price_24h": float(item.get("lowPrice24h", 0)),
            "volume_24h": float(item.get("volume24h", 0)),
            "turnover_24h": float(item.get("turnover24h", 0)),
            "mark_price": float(item.get("markPrice", 0)),
            "index_price": float(item.get("indexPrice", 0)),
            "mark_iv": float(item.get("markIv", 0)),
            "delta": float(item.get("delta", 0)),
            "gamma": float(item.get("gamma", 0)),
            "vega": float(item.get("vega", 0)),
            "theta": float(item.get("theta", 0)),
            "predicted_delivery_price": float(item.get("predictedDeliveryPrice", 0)),
            "change_24h": float(item.get("change24h", 0)),
        })

    logger.info(f"Получено тикеров: {len(tickers)}")

    return tickers
