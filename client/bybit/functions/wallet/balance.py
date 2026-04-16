"""
Получение баланса кошелька Bybit.

API: GET /v5/asset/transfer/query-account-coins-balance
Документация: https://bybit-exchange.github.io/docs/v5/asset/balance

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    account_type (str): Тип аккаунта — "UNIFIED", "CONTRACT", "SPOT", "FUND", "OPTION"
    coin (str, optional): Фильтр по валюте

Возвращает:
    list[dict]: Список балансов:
        - coin (str): Валюта
        - balance (float): Баланс
        - frozen (float): Заморожено
        - available_to_withdraw (float): Доступно для вывода
        - available_to_transfer (float): Доступно для перевода

Пример:
    balances = await get_coin_balance(client, account_type="UNIFIED")
    for b in balances:
        print(f"{b['coin']}: {b['balance']} (available: {b['available_to_withdraw']})")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_coin_balance(
    client,
    account_type: str = "UNIFIED",
    coin: str = None,
) -> list:
    """
    Получение баланса кошелька по валютам.

    Args:
        client: Экземпляр BybitClient
        account_type: Тип аккаунта
        coin: Фильтр по валюте

    Returns:
        list[dict] с данными балансов

    Raises:
        ValueError: Если account_type невалиден
        Exception: При ошибке запроса к API
    """
    valid_types = {"UNIFIED", "CONTRACT", "SPOT", "FUND", "OPTION"}
    if account_type not in valid_types:
        raise ValueError(
            f"Неподдерживаемый тип аккаунта: {account_type}. "
            f"Допустимые: {valid_types}"
        )

    params = {"accountType": account_type}
    if coin:
        params["coin"] = coin

    logger.info(f"Запрос баланса кошелька: accountType={account_type}")

    result = await client.call_private(
        method="get_coin_balance",
        params=params,
    )

    balances = []
    for item in result.get("balance", []):
        balances.append({
            "coin": item.get("coin"),
            "balance": float(item.get("balance", 0)),
            "frozen": float(item.get("frozen", 0)),
            "available_to_withdraw": float(item.get("availableToWithdraw", 0)),
            "available_to_transfer": float(item.get("availableToTransfer", 0)),
        })

    logger.info(f"Получено балансов: {len(balances)}")

    return balances
