"""
Получение списка доступных торговых инструментов (опционов).

API: public/get_instruments
Документация: https://docs.deribit.com/api-reference/market-data/public-get_instruments

Параметры:
    client (DeribitClient): Экземпляр Deribit клиента
    currency (str): Базовая валюта — "BTC" или "ETH"
    kind (str): Тип инструмента — "option" (по умолчанию)

Возвращает:
    list[dict]: Список инструментов с полями:
        - instrument_name (str): Название инструмента (напр. "BTC-27DEC24-80000-C")
        - base_currency (str): Базовая валюта
        - quote_currency (str): Валюта котировки
        - settlement_period (str): Период расчёта
        - option_type (str): "call" или "put"
        - strike (float): Цена страйка
        - tick_size (float): Минимальный шаг цены
        - contract_size (float): Размер одного контракта
        - expiration_timestamp (int): Время экспирации (мс)
        - creation_timestamp (int): Время создания инструмента
        - instrument_id (int): Внутренний ID инструмента
        - is_active (bool): Активен ли инструмент
        - min_trade_amount (float): Минимальный объём торговли

Пример:
    instruments = await get_instruments(client, "BTC")
    for inst in instruments:
        print(f"{inst['instrument_name']} | Strike: {inst['strike']} | {inst['option_type']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_instruments(client, currency: str = "BTC", kind: str = "option") -> list:
    """
    Получение списка всех доступных опционов для указанной валюты.

    Args:
        client: Экземпляр DeribitClient
        currency: "BTC" или "ETH"
        kind: "option"

    Returns:
        list[dict] с данными инструментов

    Raises:
        ValueError: Если currency или kind невалидны
        Exception: При ошибке запроса к API
    """
    if currency not in ("BTC", "ETH", "ALL"):
        raise ValueError(f"Неподдерживаемая валюта: {currency}. Используйте 'BTC', 'ETH' или 'ALL'")
    if kind != "option":
        raise ValueError(f"Для Deribit поддерживается только kind='option'")

    logger.info(f"Запрос инструментов: {currency} {kind}")

    result = await client.call_public(
        method="public/get_instruments",
        params={"currency": currency, "kind": kind}
    )

    instruments = []
    for inst in result:
        instruments.append({
            "instrument_name": inst.get("instrument_name"),
            "base_currency": inst.get("base_currency"),
            "quote_currency": inst.get("quote_currency"),
            "settlement_period": inst.get("settlement_period"),
            "option_type": inst.get("option_type"),
            "strike": inst.get("strike"),
            "tick_size": inst.get("tick_size"),
            "contract_size": inst.get("contract_size"),
            "expiration_timestamp": inst.get("expiration_timestamp"),
            "creation_timestamp": inst.get("creation_timestamp"),
            "instrument_id": inst.get("instrument_id"),
            "is_active": inst.get("is_active"),
            "min_trade_amount": inst.get("min_trade_amount"),
        })

    logger.info(f"Получено инструментов: {len(instruments)} ({currency} {kind})")

    return instruments
