"""
Получение списка доступных торговых инструментов (опционов) Bybit.

API: GET /v5/market/instruments-info
Документация: https://bybit-exchange.github.io/docs/v5/market/instrument

Для опционов используется category="option".

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    base_coin (str): Базовая валюта — "BTC" или "ETH" (по умолчанию "BTC")
    symbol (str, optional): Конкретный символ (напр. "BTC-27DEC24-80000-C")
    status (str, optional): Фильтр статуса — "Trading", "PreLaunch", "Delivering", "Settled"
    limit (int): Лимит записей (макс 1000, по умолчанию 500)
    classify (bool): Применить классификацию контрактов (по умолчанию True)

Возвращает:
    dict:
        - instruments (list[dict]): Список инструментов с классификацией:
            - symbol (str): Символ инструмента
            - options_type (str): "Call" или "Put"
            - status (str): Статус ("Trading", "PreLaunch", "Delivering", "Closed")
            - base_coin (str): Базовая валюта
            - quote_coin (str): Валюта котировки
            - settle_coin (str): Валюта расчёта
            - launch_time (int): Время запуска (мс)
            - delivery_time (int): Время доставки (мс)
            - delivery_fee_rate (float): Ставка комиссии доставки
            - original_duration_days (int): Оригинальная длительность контракта
            - days_to_expiry (int): Дней до экспирации
            - period_type (str): Тип периода (Daily, Bi-Daily, Tri-Daily, Weekly, ...)
            - period_group (str): Группа периодов (daily, weekly, monthly)
            - price_filter (dict):
                - min_price (float)
                - max_price (float)
                - tick_size (float)
            - lot_size_filter (dict):
                - max_order_qty (float)
                - min_order_qty (float)
                - qty_step (float)
        - next_page_cursor (str): Курсор для пагинации

Пример:
    result = await get_instruments(client, base_coin="BTC")
    for inst in result['instruments']:
        print(f"{inst['symbol']} | {inst['period_type']} | {inst['days_to_expiry']}d | {inst['status']}")
"""

from utils.logger import logger
from utils.timer import timed_execution
from utils.option_classifier import classify_bybit_option


@timed_execution
async def get_instruments(
    client,
    base_coin: str = "BTC",
    symbol: str = None,
    status: str = None,
    limit: int = 500,
    classify: bool = True,
) -> dict:
    """
    Получение списка всех доступных опционов.

    Args:
        client: Экземпляр BybitClient
        base_coin: "BTC" или "ETH"
        symbol: Конкретный символ (опционально)
        status: Фильтр статуса (опционально)
        limit: Лимит записей (макс 1000)
        classify: Применить классификацию контрактов (по умолчанию True)

    Returns:
        dict с данными инструментов и классификацией

    Raises:
        ValueError: Если base_coin невалиден или limit > 1000
        Exception: При ошибке запроса к API
    """
    if base_coin not in ("BTC", "ETH"):
        raise ValueError(
            f"Неподдерживаемая базовая валюта: {base_coin}. "
            f"Используйте 'BTC' или 'ETH'"
        )
    if limit > 1000:
        raise ValueError(f"Максимальный лимит: 1000. Получено: {limit}")

    params = {
        "category": "option",
        "baseCoin": base_coin,
        "limit": str(limit),
    }

    if symbol:
        params["symbol"] = symbol
    if status:
        params["status"] = status

    logger.info(
        f"Запрос инструментов: category=option, baseCoin={base_coin}, classify={classify}"
    )

    result = await client.call_public(
        method="get_instruments_info",
        params=params,
    )

    instruments = []
    for inst in result.get("list", []):
        price_filter = inst.get("priceFilter", {})
        lot_filter = inst.get("lotSizeFilter", {})

        # Базовая информация
        instrument_data = {
            "symbol": inst.get("symbol"),
            "options_type": inst.get("optionsType"),
            "raw_status": inst.get("status"),
            "base_coin": inst.get("baseCoin"),
            "quote_coin": inst.get("quoteCoin"),
            "settle_coin": inst.get("settleCoin"),
            "launch_time": int(inst["launchTime"]) if inst.get("launchTime") else None,
            "delivery_time": int(inst["deliveryTime"]) if inst.get("deliveryTime") else None,
            "delivery_fee_rate": float(inst.get("deliveryFeeRate", 0)),
            "price_filter": {
                "min_price": float(price_filter.get("minPrice", 0)),
                "max_price": float(price_filter.get("maxPrice", 0)),
                "tick_size": float(price_filter.get("tickSize", 0)),
            },
            "lot_size_filter": {
                "max_order_qty": float(lot_filter.get("maxOrderQty", 0)),
                "min_order_qty": float(lot_filter.get("minOrderQty", 0)),
                "qty_step": float(lot_filter.get("qtyStep", 0)),
            },
        }

        # Применяем классификацию если запрошено
        if classify:
            classified = classify_bybit_option(inst)
            # Объединяем данные
            instrument_data.update({
                "status": classified["status"],
                "original_duration_days": classified["original_duration_days"],
                "days_to_expiry": classified["days_to_expiry"],
                "period_type": classified["period_type"],
                "period_group": classified["period_group"],
                "is_daily_type": classified["is_daily_type"],
                "expiry_date": classified["expiry_date"],
                "launch_date": classified["launch_date"],
                "strike": classified["strike"],
            })
        else:
            # Без классификации - базовые поля
            instrument_data.update({
                "status": inst.get("status"),
                "original_duration_days": None,
                "days_to_expiry": None,
                "period_type": None,
                "period_group": None,
                "is_daily_type": None,
                "expiry_date": None,
                "launch_date": None,
                "strike": None,
            })

        instruments.append(instrument_data)

    logger.info(
        f"Получено инструментов: {len(instruments)} | "
        f"baseCoin={base_coin} | nextCursor={result.get('nextPageCursor')} | classified={classify}"
    )

    return {
        "instruments": instruments,
        "next_page_cursor": result.get("nextPageCursor"),
    }
