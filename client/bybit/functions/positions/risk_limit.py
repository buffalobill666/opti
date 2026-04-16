"""
Установка лимита риска (risk limit) для позиции Bybit.

API: POST /v5/position/set-risk-limit
Документация: https://bybit-exchange.github.io/docs/v5/position/risk-limit

Для опционов используется category="option".

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    symbol (str): Символ инструмента
    risk_id (int): ID лимита риска
    position_idx (int, optional): Индекс позиции (0 = одна позиция)

Возвращает:
    dict:
        - category (str): Категория
        - risk_id (int): Новый ID лимита риска

Пример:
    result = await set_risk_limit(client, symbol="BTC-27DEC24-80000-C", risk_id=1)
    print(f"Risk limit установлен: {result['risk_id']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def set_risk_limit(
    client,
    symbol: str,
    risk_id: int,
    position_idx: int = 0,
) -> dict:
    """
    Установка лимита риска для позиции.

    Args:
        client: Экземпляр BybitClient
        symbol: Символ инструмента
        risk_id: ID лимита риска
        position_idx: Индекс позиции

    Returns:
        dict с результатами

    Raises:
        Exception: При ошибке запроса к API
    """
    params = {
        "category": "option",
        "symbol": symbol,
        "riskId": risk_id,
    }

    if position_idx:
        params["positionIdx"] = position_idx

    logger.info(
        f"Установка risk limit: {symbol} | risk_id={risk_id}"
    )

    result = await client.call_private(
        method="set_risk_limit",
        params=params,
    )

    risk_result = {
        "category": result.get("category"),
        "risk_id": result.get("riskId"),
    }

    logger.info(
        f"Risk limit установлен: {symbol} | risk_id={risk_result['risk_id']}"
    )

    return risk_result
