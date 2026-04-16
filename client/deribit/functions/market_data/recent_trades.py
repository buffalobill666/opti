"""
Получение последних сделок для опционов Deribit.

API: public/get_last_trades_by_instrument
Документация: https://docs.deribit.com/api-reference/market-data/public-get_last_trades_by_instrument

Параметры:
    client (DeribitClient): Экземпляр Deribit клиента
    instrument_name (str): Название инструмента (напр. "BTC-27DEC24-80000-C")
    start_id (int, optional): ID первой сделки (для пагинации)
    end_id (int, optional): ID последней сделки (для пагинации)
    count (int): Количество записей (макс 1000, по умолчанию 50)
    include_old (bool): Включать старые сделки (по умолчанию False)

Возвращает:
    dict:
        - trades (list[dict]): Список последних сделок:
            - trade_id (str): ID сделки
            - instrument_name (str): Название инструмента
            - price (float): Цена сделки
            - amount (float): Размер сделки
            - direction (str): Направление — "buy" или "sell"
            - tick_direction (int): Направление тика (0-3)
            - timestamp (int): Время сделки (мс)
            - iv (float): Подразумеваемая волатильность
            - mark_price (float): Mark price на момент сделки
        - has_more (bool): Есть ли ещё сделки для пагинации

Пример:
    result = await get_recent_trades(client, instrument_name="BTC-27DEC24-80000-C", count=10)
    for t in result['trades']:
        print(f"{t['direction']} {t['amount']} @ {t['price']} | IV: {t['iv']}%")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_recent_trades(
    client,
    instrument_name: str,
    start_id: int = None,
    end_id: int = None,
    count: int = 50,
    include_old: bool = False,
) -> dict:
    """
    Получение последних сделок по опциону.

    Args:
        client: Экземпляр DeribitClient
        instrument_name: Название инструмента
        start_id: ID первой сделки
        end_id: ID последней сделки
        count: Количество записей (макс 1000)
        include_old: Включать старые сделки

    Returns:
        dict с данными сделок

    Raises:
        ValueError: Если count > 1000
        Exception: При ошибке запроса к API
    """
    if count > 1000:
        raise ValueError(f"Максимальный лимит: 1000. Получено: {count}")

    params = {
        "instrument_name": instrument_name,
        "count": count,
        "include_old": include_old,
    }

    if start_id is not None:
        params["start_id"] = start_id
    if end_id is not None:
        params["end_id"] = end_id

    logger.info(f"Запрос последних сделок: {instrument_name}")

    result = await client.call_public(
        method="public/get_last_trades_by_instrument",
        params=params,
    )

    trades = []
    for item in result.get("trades", []):
        trades.append({
            "trade_id": item.get("trade_id"),
            "instrument_name": item.get("instrument_name"),
            "price": item.get("price"),
            "amount": item.get("amount"),
            "direction": item.get("direction"),
            "tick_direction": item.get("tick_direction"),
            "timestamp": item.get("timestamp"),
            "iv": item.get("iv"),
            "mark_price": item.get("mark_price"),
        })

    logger.info(
        f"Получено сделок: {len(trades)} | "
        f"has_more={result.get('hasMore', False)}"
    )

    return {
        "trades": trades,
        "has_more": result.get("hasMore", False),
    }
