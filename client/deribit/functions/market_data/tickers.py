"""
Получение последних котировок (тикеров) для опционов.

API: public/get_book_summary_by_currency
Документация: https://docs.deribit.com/api-reference/market-data/public-get_book_summary_by_currency

Параметры:
    client (DeribitClient): Экземпляр Deribit клиента
    currency (str): Базовая валюта — "BTC" или "ETH"
    kind (str): Тип инструмента — "option" (по умолчанию)

Возвращает:
    list[dict]: Список тикеров для каждого инструмента:
        - instrument_name (str): Название инструмента
        - mark_price (float): Mark price
        - mark_iv (float): Подразумеваемая волатильность (mark)
        - best_bid_price (float): Лучшая цена покупки
        - best_bid_amount (float): Объём лучшей покупки
        - best_ask_price (float): Лучшая цена продажи
        - best_ask_amount (float): Объём лучшей продажи
        - last_price (float): Цена последней сделки
        - volume (float): Объём за 24ч
        - volume_usd (float): Объём за 24ч в USD
        - open_interest (float): Объём открытых позиций
        - underlying_price (float): Цена базового актива
        - underlying_index (str): Индекс базового актива
        - interest_rate (float): Процентная ставка
        - greeks (dict): Греки опциона:
            - delta (float)
            - gamma (float)
            - rho (float)
            - theta (float)
            - vega (float)

Пример:
    tickers = await get_tickers(client, "BTC")
    for t in tickers:
        print(f"{t['instrument_name']} | Mark: {t['mark_price']} | IV: {t['mark_iv']}%")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_tickers(client, currency: str = "BTC", kind: str = "option") -> list:
    """
    Получение сводки по всем опционам для указанной валюты.

    Args:
        client: Экземпляр DeribitClient
        currency: "BTC" или "ETH"
        kind: "option"

    Returns:
        list[dict] с данными тикеров

    Raises:
        ValueError: Если currency невалидна
        Exception: При ошибке запроса к API
    """
    if currency not in ("BTC", "ETH", "ALL"):
        raise ValueError(
            f"Неподдерживаемая валюта: {currency}. "
            f"Используйте 'BTC', 'ETH' или 'ALL'"
        )

    logger.info(f"Запрос тикеров: {currency} {kind}")

    result = await client.call_public(
        method="public/get_book_summary_by_currency",
        params={"currency": currency, "kind": kind}
    )

    tickers = []
    for item in result:
        greeks = item.get("greeks", {})
        tickers.append({
            "instrument_name": item.get("instrument_name"),
            "mark_price": item.get("mark_price"),
            "mark_iv": item.get("mark_iv"),
            "best_bid_price": item.get("best_bid_price"),
            "best_bid_amount": item.get("best_bid_amount"),
            "best_ask_price": item.get("best_ask_price"),
            "best_ask_amount": item.get("best_ask_amount"),
            "last_price": item.get("last_price"),
            "volume": item.get("volume"),
            "volume_usd": item.get("volume_usd"),
            "open_interest": item.get("open_interest"),
            "underlying_price": item.get("underlying_price"),
            "underlying_index": item.get("underlying_index"),
            "interest_rate": item.get("interest_rate"),
            "greeks": {
                "delta": greeks.get("delta"),
                "gamma": greeks.get("gamma"),
                "rho": greeks.get("rho"),
                "theta": greeks.get("theta"),
                "vega": greeks.get("vega"),
            },
        })

    logger.info(f"Получено тикеров: {len(tickers)} ({currency} {kind})")

    return tickers
