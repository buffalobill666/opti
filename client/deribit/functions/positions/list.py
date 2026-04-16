"""
Получение списка открытых позиций по опционам Deribit.

API: private/get_positions
Документация: https://docs.deribit.com/api-reference/account-management/private-get_positions

Параметры:
    client (DeribitClient): Экземпляр Deribit клиента
    currency (str): Базовая валюта — "BTC", "ETH" или "ALL"
    kind (str): Тип инструмента — "option" (по умолчанию)

Возвращает:
    list[dict]: Список позиций с полями:
        - instrument_name (str): Название инструмента
        - size (float): Размер позиции (контракты, может быть отрицательным)
        - average_price (float): Средняя цена открытия
        - mark_price (float): Текущая mark price
        - unrealized_pnl (float): Нереализованный P&L
        - realized_pnl (float): Реализованный P&L
        - settlement_price (float): Цена расчёта (если закрыта)
        - delta (float): Дельта позиции
        - gamma (float): Гамма позиции
        - theta (float): Тета позиции
        - vega (float): Вега позиции
        - rho (float): Ро позиции
        - kind (str): Тип — "option"
        - direction (str): Направление — "buy" или "sell"

Пример:
    positions = await get_positions(client, currency="BTC")
    for pos in positions:
        print(f"{pos['instrument_name']} | Size: {pos['size']} | "
              f"P&L: {pos['unrealized_pnl']} | Delta: {pos['delta']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_positions(
    client,
    currency: str = "ALL",
    kind: str = "option"
) -> list:
    """
    Получение всех открытых позиций по опционам.

    Args:
        client: Экземпляр DeribitClient
        currency: "BTC", "ETH" или "ALL"
        kind: "option"

    Returns:
        list[dict] с данными позиций

    Raises:
        ValueError: Если currency невалидна
        Exception: При ошибке запроса к API
    """
    if currency not in ("BTC", "ETH", "ALL"):
        raise ValueError(
            f"Неподдерживаемая валюта: {currency}. "
            f"Используйте 'BTC', 'ETH' или 'ALL'"
        )

    logger.info(f"Запрос позиций: {currency} {kind}")

    result = await client.call_private(
        method="private/get_positions",
        params={
            "currency": currency,
            "kind": kind,
        }
    )

    positions = []
    for item in result:
        positions.append({
            "instrument_name": item.get("instrument_name"),
            "size": item.get("size"),
            "average_price": item.get("average_price"),
            "mark_price": item.get("mark_price"),
            "unrealized_pnl": item.get("unrealized_pnl"),
            "realized_pnl": item.get("realized_pnl"),
            "settlement_price": item.get("settlement_price"),
            "delta": item.get("delta"),
            "gamma": item.get("gamma"),
            "theta": item.get("theta"),
            "vega": item.get("vega"),
            "rho": item.get("rho"),
            "kind": item.get("kind"),
            "direction": item.get("direction"),
        })

    logger.info(
        f"Получено позиций: {len(positions)} | "
        f"currency={currency}"
    )

    return positions
