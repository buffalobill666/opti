"""
Получение информации о залоговых монетах Bybit.

API: GET /v5/account/collateral-info
Документация: https://bybit-exchange.github.io/docs/v5/account/collateral

Для опционов используется Unified Trading Account.

Параметры:
    client (BybitClient): Экземпляр Bybit клиента

Возвращает:
    list[dict]: Список залоговых монет:
        - currency (str): Валюта
        - collateral_ratio (float): Коэффициент залога
        - collateral_switch (bool): Переключатель залога
        - hourly_borrow_rate (float): Часовая ставка займа
        - max_collateral (float): Максимальный залог

Пример:
    collateral = await get_collateral_info(client)
    for c in collateral:
        print(f"{c['currency']} | Ratio: {c['collateral_ratio']} | Switch: {c['collateral_switch']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_collateral_info(client) -> list:
    """
    Получение информации о залоговых монетах.

    Args:
        client: Экземпляр BybitClient

    Returns:
        list[dict] с данными залогов

    Raises:
        Exception: При ошибке запроса к API
    """
    logger.info("Запрос информации о залоговых монетах")

    result = await client.call_private(
        method="get_collateral_info",
        params={},
    )

    collateral = []
    for item in result.get("list", []):
        collateral.append({
            "currency": item.get("currency"),
            "collateral_ratio": float(item.get("collateralRatio", 0)),
            "collateral_switch": item.get("collateralSwitch"),
            "hourly_borrow_rate": float(item.get("hourlyBorrowRate", 0)),
            "max_collateral": float(item.get("maxCollateral", 0)),
        })

    logger.info(f"Получено залоговых монет: {len(collateral)}")

    return collateral
