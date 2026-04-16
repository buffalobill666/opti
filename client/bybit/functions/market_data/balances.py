"""
Получение баланса аккаунта Bybit.

API: GET /v5/account/wallet
Документация: https://bybit-exchange.github.io/docs/v5/account/wallet-balance

Для опционов используется accountType="UNIFIED" (Unified Trading Account).
Опционы Bybit торгуются в USDC.

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    account_type (str): Тип аккаунта — "UNIFIED" (по умолчанию)
    coin (str, optional): Фильтр по валюте — "USDC", "BTC", "ETH", "USDT"

Возвращает:
    dict:
        - account_type (str): Тип аккаунта
        - coins (list[dict]): Список валют с балансами:
            - coin (str): Валюта
            - equity (float): Эквити
            - usd_value (float): Стоимость в USD
            - wallet_balance (float): Баланс кошелька
            - available_to_withdraw (float): Доступно для вывода
            - available_to_borrow (float): Доступно для займа
            - unrealised_pnl (float): Нереализованный P&L
            - perp_pnl (float): P&L бессрочных
            - futures_pnl (float): P&L фьючерсов
            - options_pnl (float): P&L опционов
            - bonus (float): Бонус
            - collateral_switch (bool): Переключатель залога
            - margin_collateral (float): Маржинальный залог
            - maintenance_margin (float): Минимальная маржа
            - initial_margin (float): Начальная маржа
            - total_order_im (float): Начальная маржа ордеров
            - adl_indicator (float): Индикатор ADL

Пример:
    balance = await get_wallet_balance(client, account_type="UNIFIED", coin="USDC")
    for c in balance['coins']:
        print(f"{c['coin']}: equity={c['equity']}, available={c['available_to_withdraw']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


def _safe_float(value, default=0.0) -> float:
    """Безопасное преобразование в float, обработка пустых строк."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_bool(value, default=False) -> bool:
    """Безопасное преобразование в bool."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1", "yes")


@timed_execution
async def get_wallet_balance(
    client,
    account_type: str = "UNIFIED",
    coin: str = None,
) -> dict:
    """
    Получение баланса кошелька.

    Args:
        client: Экземпляр BybitClient
        account_type: "UNIFIED" для опционов
        coin: Фильтр по валюте (опционально)

    Returns:
        dict с данными баланса

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

    logger.info(f"Запрос баланса: accountType={account_type}, coin={coin or 'ALL'}")

    result = await client.call_private(
        method="get_wallet_balance",
        params=params,
    )

    list_data = result.get("list", [])
    if not list_data:
        logger.warning("Пустой ответ баланса")
        return {"account_type": account_type, "coins": []}

    account = list_data[0]
    coins = []

    for c in account.get("coin", []):
        coins.append({
            "coin": c.get("coin"),
            "equity": _safe_float(c.get("equity")),
            "usd_value": _safe_float(c.get("usdValue")),
            "wallet_balance": _safe_float(c.get("walletBalance")),
            "available_to_withdraw": _safe_float(c.get("availableToWithdraw")),
            "available_to_borrow": _safe_float(c.get("availableToBorrow")),
            "unrealised_pnl": _safe_float(c.get("unrealisedPnl")),
            "perp_pnl": _safe_float(c.get("perpPnl")),
            "futures_pnl": _safe_float(c.get("futuresPnl")),
            "options_pnl": _safe_float(c.get("optionsPnl")),
            "bonus": _safe_float(c.get("bonus")),
            "collateral_switch": _safe_bool(c.get("collateralSwitch")),
            "margin_collateral": _safe_float(c.get("marginCollateral")),
            "maintenance_margin": _safe_float(c.get("maintenanceMargin")),
            "initial_margin": _safe_float(c.get("initialMargin")),
            "total_order_im": _safe_float(c.get("totalOrderIM")),
            "adl_indicator": _safe_float(c.get("adlIndicator")),
        })

    logger.info(
        f"Баланс {account_type}: {len(coins)} валют | "
        f"USDC equity={next((c['equity'] for c in coins if c['coin'] == 'USDC'), 0)}"
    )

    return {
        "account_type": account_type,
        "coins": coins,
    }
