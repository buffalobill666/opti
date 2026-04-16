"""
Получение баланса аккаунта Deribit.

API: private/get_account_summary
Документация: https://docs.deribit.com/api-reference/account-management/private-get_account_summary

Параметры:
    client (DeribitClient): Экземпляр Deribit клиента
    currency (str): Валюта — "BTC" или "ETH"

Возвращает:
    dict:
        - balance (float): Текущий баланс
        - equity (float): Эквити (баланс + нереализованный P&L)
        - margin_balance (float): Баланс с учётом маржи
        - available_funds (float): Доступные средства для новых позиций
        - initial_margin (float): Начальная маржа (открытые позиции)
        - maintenance_margin (float): Минимальная маржа для поддержания позиций
        - delta_total (float): Суммарная дельта портфеля
        - options_vega (float): Суммарная вега опционов
        - options_delta (float): Суммарная дельта опционов
        - options_gamma (float): Суммарная гамма опционов
        - options_theta (float): Суммарная тета опционов

Пример ответа:
    {
        "balance": 1.2345,
        "equity": 1.2500,
        "margin_balance": 1.2400,
        "available_funds": 0.8000,
        "initial_margin": 0.4000,
        "maintenance_margin": 0.2000,
        "delta_total": 0.05,
        "options_vega": 12.5,
        "options_delta": 0.03,
        "options_gamma": 0.01,
        "options_theta": -0.5
    }
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_account_summary(client, currency: str) -> dict:
    """
    Получение сводки по аккаунту для указанной валюты.

    Args:
        client: Экземпляр DeribitClient
        currency: "BTC" или "ETH"

    Returns:
        dict с данными баланса

    Raises:
        ValueError: Если currency не "BTC" или "ETH"
        Exception: При ошибке запроса к API
    """
    if currency not in ("BTC", "ETH"):
        raise ValueError(f"Неподдерживаемая валюта: {currency}. Используйте 'BTC' или 'ETH'")

    logger.info(f"Запрос баланса: {currency}")

    result = await client.call_private(
        method="private/get_account_summary",
        params={"currency": currency}
    )

    summary = {
        "balance": result.get("balance"),
        "equity": result.get("equity"),
        "margin_balance": result.get("margin_balance"),
        "available_funds": result.get("available_funds"),
        "initial_margin": result.get("initial_margin"),
        "maintenance_margin": result.get("maintenance_margin"),
        "delta_total": result.get("delta_total"),
        "options_vega": result.get("options_vega"),
        "options_delta": result.get("options_delta"),
        "options_gamma": result.get("options_gamma"),
        "options_theta": result.get("options_theta"),
    }

    logger.info(
        f"Баланс {currency}: equity={summary['equity']}, "
        f"available={summary['available_funds']}, margin={summary['initial_margin']}"
    )

    return summary
