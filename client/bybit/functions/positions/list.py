"""
Получение списка открытых позиций по опционам Bybit.

API: GET /v5/position/list
Документация: https://bybit-exchange.github.io/docs/v5/position

Для опционов используется category="option".

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    symbol (str, optional): Символ инструмента
    base_coin (str, optional): Базовая валюта — "BTC" или "ETH"
    limit (int, optional): Лимит записей (макс 200)
    cursor (str, optional): Курсор для пагинации

Возвращает:
    dict:
        - positions (list[dict]): Список позиций:
            - symbol (str): Символ инструмента
            - side (str): Направление — "Buy" или "Sell"
            - size (str): Размер позиции
            - avg_entry_price (str): Средняя цена входа
            - mark_price (str): Mark price
            - unrealised_pnl (str): Нереализованный P&L
            - realised_pnl (str): Реализованный P&L
            - cumulative_realised_pnl (str): Кумулятивный реализованный P&L
            - position_value (str): Стоимость позиции
            - position_balance (str): Баланс позиции
            - mmr (str): Минимальная маржа
            - imr (str): Начальная маржа
            - leverage (str): Кредитное плечо
            - auto_add_margin (str): Автоматическое добавление маржи
            - adl_rank_indicator (int): Индикатор ADL
            - created_time (str): Время создания
            - updated_time (str): Время обновления
            - delta (str): Дельта
            - gamma (str): Гамма
            - vega (str): Вега
            - theta (str): Тета
        - next_page_cursor (str): Курсор для пагинации

Пример:
    result = await get_positions(client, base_coin="BTC")
    for pos in result['positions']:
        print(f"{pos['symbol']} | Size: {pos['size']} | "
              f"P&L: {pos['unrealised_pnl']} | Delta: {pos['delta']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_positions(
    client,
    symbol: str = None,
    base_coin: str = None,
    limit: int = None,
    cursor: str = None,
) -> dict:
    """
    Получение всех открытых позиций по опционам.

    Args:
        client: Экземпляр BybitClient
        symbol: Символ инструмента
        base_coin: "BTC" или "ETH"
        limit: Лимит записей (макс 200)
        cursor: Курсор для пагинации

    Returns:
        dict с данными позиций

    Raises:
        ValueError: Если limit > 200
        Exception: При ошибке запроса к API
    """
    if limit and limit > 200:
        raise ValueError(f"Максимальный лимит: 200. Получено: {limit}")

    params = {"category": "option"}

    if symbol:
        params["symbol"] = symbol
    if base_coin:
        params["baseCoin"] = base_coin
    if limit:
        params["limit"] = str(limit)
    if cursor:
        params["cursor"] = cursor

    logger.info(
        f"Запрос позиций: category=option | "
        f"baseCoin={base_coin or 'ALL'}"
    )

    result = await client.call_private(
        method="get_positions",
        params=params,
    )

    positions = []
    for item in result.get("list", []):
        positions.append({
            "symbol": item.get("symbol"),
            "side": item.get("side"),
            "size": item.get("size"),
            "avg_entry_price": item.get("avgEntryPrice"),
            "mark_price": item.get("markPrice"),
            "unrealised_pnl": item.get("unrealisedPnl"),
            "realised_pnl": item.get("cumRealisedPnl"),
            "cumulative_realised_pnl": item.get("cumRealisedPnl"),
            "position_value": item.get("positionValue"),
            "position_balance": item.get("positionBalance"),
            "mmr": item.get("mmr"),
            "imr": item.get("imr"),
            "leverage": item.get("leverage"),
            "auto_add_margin": item.get("autoAddMargin"),
            "adl_rank_indicator": int(item.get("adlRankIndicator", 0)),
            "created_time": item.get("createdTime"),
            "updated_time": item.get("updatedTime"),
            "delta": item.get("delta"),
            "gamma": item.get("gamma"),
            "vega": item.get("vega"),
            "theta": item.get("theta"),
        })

    logger.info(
        f"Получено позиций: {len(positions)} | "
        f"baseCoin={base_coin or 'ALL'}"
    )

    return {
        "positions": positions,
        "next_page_cursor": result.get("nextPageCursor"),
    }
