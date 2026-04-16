"""
Создание внутреннего перевода на Bybit.

API: POST /v5/asset/transfer/inter-transfer
Документация: https://bybit-exchange.github.io/docs/v5/asset/inter-transfer

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    transfer_id (str): Уникальный ID перевода
    coin (str): Валюта — "USDC", "BTC", "ETH", "USDT"
    amount (str): Сумма перевода
    from_account_type (str): Тип источника — "UNIFIED", "CONTRACT", "SPOT", "FUND", "OPTION"
    to_account_type (str): Тип назначения — "UNIFIED", "CONTRACT", "SPOT", "FUND", "OPTION"

Возвращает:
    dict:
        - transfer_id (str): ID перевода
        - status (str): Состояние — "SUCCESS", "PENDING", "FAILED"

Пример:
    result = await create_transfer(
        client,
        coin="USDC",
        amount="1000",
        from_account_type="UNIFIED",
        to_account_type="CONTRACT"
    )
    print(f"Transfer {result['transfer_id']} status: {result['status']}")
"""

import uuid

from utils.logger import logger
from utils.timer import timed_execution


# Допустимые типы аккаунтов
VALID_ACCOUNT_TYPES = {"UNIFIED", "CONTRACT", "SPOT", "FUND", "OPTION"}


@timed_execution
async def create_transfer(
    client,
    coin: str,
    amount: str,
    from_account_type: str,
    to_account_type: str,
    transfer_id: str = None,
) -> dict:
    """
    Создание внутреннего перевода.

    Args:
        client: Экземпляр BybitClient
        coin: Валюта
        amount: Сумма
        from_account_type: Тип источника
        to_account_type: Тип назначения
        transfer_id: Уникальный ID (генерируется если None)

    Returns:
        dict с данными перевода

    Raises:
        ValueError: Если account_type невалиден
        Exception: При ошибке запроса к API
    """
    if from_account_type not in VALID_ACCOUNT_TYPES:
        raise ValueError(
            f"Неподдерживаемый источник: {from_account_type}. "
            f"Допустимые: {VALID_ACCOUNT_TYPES}"
        )
    if to_account_type not in VALID_ACCOUNT_TYPES:
        raise ValueError(
            f"Неподдерживаемое назначение: {to_account_type}. "
            f"Допустимые: {VALID_ACCOUNT_TYPES}"
        )
    if from_account_type == to_account_type:
        raise ValueError(f"Источник и назначение совпадают: {from_account_type}")

    if transfer_id is None:
        transfer_id = f"runner_{uuid.uuid4().hex[:16]}"

    logger.info(
        f"Создание перевода: {amount} {coin} | "
        f"{from_account_type} → {to_account_type}"
    )

    result = await client.call_private(
        method="create_internal_transfer",
        params={
            "transferId": transfer_id,
            "coin": coin,
            "amount": amount,
            "fromAccountType": from_account_type,
            "toAccountType": to_account_type,
        },
    )

    transfer = {
        "transfer_id": result.get("transferId"),
        "status": result.get("status", "SUCCESS"),
    }

    logger.info(
        f"Перевод создан: {transfer['transfer_id']} | "
        f"status={transfer['status']}"
    )

    return transfer
