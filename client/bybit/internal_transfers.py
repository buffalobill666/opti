"""
Внутренние переводы Bybit.

API: POST /v5/asset/transfer/inter-transfer
Документация: https://bybit-exchange.github.io/docs/v5/asset/inter-transfer

Bybit использует Unified Trading Account — все средства на едином счёте.
Внутренние переводы нужны для перемещения между:
    - SPOT       — спотовый кошелёк
    - CONTRACT   — кошелёк деривативов (фьючерсы, опционы)
    - UNIFIED    — унифицированный кошелёк
    - FUND       — кошелёк финансирования (ввод/вывод)
    - OPTION     — кошелёк опционов (USDC)

Параметры перевода:
    client (BybitClient): Экземпляр Bybit клиента
    transfer_id (str): Уникальный ID перевода (генерируется клиентом)
    coin (str): Валюта — "USDC", "BTC", "ETH", "USDT"
    amount (str): Сумма перевода
    from_account_type (str): Тип источника — "UNIFIED", "CONTRACT", "SPOT", "FUND", "OPTION"
    to_account_type (str): Тип назначения — "UNIFIED", "CONTRACT", "SPOT", "FUND", "OPTION"

Возвращает:
    dict:
        - transferId (str): ID перевода
        - status (str): Состояние — "SUCCESS", "PENDING", "FAILED"

Пример:
    # Перевести 1000 USDC из UNIFIED в CONTRACT (для опционов)
    result = await transfer(
        client,
        transfer_id="transfer_001",
        coin="USDC",
        amount="1000",
        from_account_type="UNIFIED",
        to_account_type="CONTRACT"
    )
    print(f"Transfer {result['transferId']} status: {result['status']}")
"""

import uuid

from utils.logger import logger
from utils.timer import timed_execution


# Допустимые типы аккаунтов
VALID_ACCOUNT_TYPES = {"UNIFIED", "CONTRACT", "SPOT", "FUND", "OPTION"}


@timed_execution
async def transfer(
    client,
    coin: str,
    amount: str,
    from_account_type: str,
    to_account_type: str,
    transfer_id: str = None,
) -> dict:
    """
    Выполнение внутреннего перевода между кошельками Bybit.

    Args:
        client: Экземпляр BybitClient
        coin: Валюта — "USDC", "BTC", "ETH", "USDT"
        amount: Сумма перевода (строка)
        from_account_type: Тип источника
        to_account_type: Тип назначения
        transfer_id: Уникальный ID (генерируется автоматически если None)

    Returns:
        dict с данными перевода

    Raises:
        ValueError: Если account_type невалиден
        Exception: При ошибке запроса к API
    """
    # Валидация
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
        raise ValueError(
            f"Источник и назначение совпадают: {from_account_type}"
        )

    # Генерация transfer_id если не указан
    if transfer_id is None:
        transfer_id = f"options_runner_{uuid.uuid4().hex[:16]}"

    logger.info(
        f"Перевод Bybit: {amount} {coin} | "
        f"{from_account_type} → {to_account_type} | "
        f"id={transfer_id}"
    )

    result = await client.call_private(
        method="create_internal_transfer",
        params={
            "transferId": transfer_id,
            "coin": coin,
            "amount": amount,
            "fromAccountType": from_account_type,
            "toAccountType": to_account_type,
        }
    )

    transfer_data = {
        "transferId": result.get("transferId"),
        "status": result.get("status", "SUCCESS"),
    }

    logger.info(
        f"Перевод выполнен: {transfer_data['transferId']} | "
        f"{amount} {coin} | "
        f"{from_account_type} → {to_account_type} | "
        f"status={transfer_data['status']}"
    )

    return transfer_data


@timed_execution
async def get_transfers(
    client,
    transfer_id: str = None,
    coin: str = None,
    status: str = None,
    start_time: int = None,
    end_time: int = None,
    limit: int = 20,
) -> list:
    """
    Получение истории внутренних переводов.

    API: GET /v5/asset/transfer/query-inter-transfer-list
    Документация: https://bybit-exchange.github.io/docs/v5/asset/inter-transfer-list

    Args:
        client: Экземпляр BybitClient
        transfer_id: Фильтр по ID перевода
        coin: Фильтр по валюте
        status: Фильтр по статусу — "SUCCESS", "PENDING", "FAILED"
        start_time: Время начала (мс)
        end_time: Время окончания (мс)
        limit: Количество записей (макс 50)

    Returns:
        list[dict] с данными переводов

    Raises:
        ValueError: Если limit > 50
        Exception: При ошибке запроса к API
    """
    if limit > 50:
        raise ValueError(f"Максимальное количество записей: 50. Получено: {limit}")

    params = {"limit": str(limit)}

    if transfer_id:
        params["transferId"] = transfer_id
    if coin:
        params["coin"] = coin
    if status:
        params["status"] = status
    if start_time:
        params["startTime"] = str(start_time)
    if end_time:
        params["endTime"] = str(end_time)

    logger.info(f"Запрос истории переводов Bybit: {params}")

    result = await client.call_private(
        method="get_transfer_history",
        params=params,
    )

    transfers = []
    list_data = result.get("list", [])

    for item in list_data:
        transfers.append({
            "transferId": item.get("transferId"),
            "coin": item.get("coin"),
            "amount": item.get("amount"),
            "fromAccountType": item.get("fromAccountType"),
            "toAccountType": item.get("toAccountType"),
            "status": item.get("status"),
            "timestamp": item.get("timestamp"),
        })

    logger.info(f"Получено переводов Bybit: {len(transfers)}")

    return transfers
