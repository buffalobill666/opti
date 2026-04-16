"""
Получение ставки комиссий для опционов Bybit.

API: GET /v5/account/fee-rate
Документация: https://bybit-exchange.github.io/docs/v5/account/fee-rate

Для опционов используется category="option".

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    symbol (str, optional): Символ инструмента
    base_coin (str, optional): Базовая валюта — "BTC" или "ETH"

Возвращает:
    list[dict]: Список ставок комиссий:
        - symbol (str): Символ инструмента
        - base_coin (str): Базовая валюта
        - maker_fee_rate (float): Ставка комиссии мейкера
        - taker_fee_rate (float): Ставка комиссии тейкера

Пример:
    fees = await get_fee_rate(client, base_coin="BTC")
    for f in fees:
        print(f"{f['symbol']} | Maker: {f['maker_fee_rate']} | Taker: {f['taker_fee_rate']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def get_fee_rate(
    client,
    symbol: str = None,
    base_coin: str = None,
) -> list:
    """
    Получение ставок комиссий для опционов.

    Args:
        client: Экземпляр BybitClient
        symbol: Символ инструмента
        base_coin: "BTC" или "ETH"

    Returns:
        list[dict] с данными комиссий

    Raises:
        Exception: При ошибке запроса к API
    """
    params = {"category": "option"}

    if symbol:
        params["symbol"] = symbol
    if base_coin:
        params["baseCoin"] = base_coin

    logger.info(f"Запрос ставок комиссий: category=option")

    result = await client.call_private(
        method="get_account_info",
        params=params,
    )

    # Bybit возвращает fee rate в account info
    fee_rates = []
    for item in result.get("list", []):
        fee_rates.append({
            "symbol": item.get("symbol"),
            "base_coin": item.get("baseCoin"),
            "maker_fee_rate": float(item.get("makerFeeRate", 0)),
            "taker_fee_rate": float(item.get("takerFeeRate", 0)),
        })

    logger.info(f"Получено ставок комиссий: {len(fee_rates)}")

    return fee_rates
