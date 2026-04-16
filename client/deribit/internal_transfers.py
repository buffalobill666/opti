"""
Внутренние переводы между кошельками Deribit.

API: private/transfer
Документация: https://docs.deribit.com/api-reference/wallet/private-transfer

Deribit имеет следующие типы кошельков:
    - funding    — основной кошелёк (ввод/вывод)
    - spot       — спотовая торговля
    - future     — фьючерсная торговля
    - option     — опционная маржа

Параметры перевода:
    client (DeribitClient): Экземпляр Deribit клиента
    currency (str): Валюта — "BTC" или "ETH"
    amount (float): Сумма перевода
    destination (str): Тип кошелька назначения — "funding", "spot", "future", "option"
    source (str): Тип кошелька источника — "funding", "spot", "future", "option"

Возвращает:
    dict:
        - id (str): ID перевода
        - currency (str): Валюта
        - amount (float): Сумма
        - source (str): Кошелёк источника
        - destination (str): Кошелёк назначения
        - state (str): Состояние — "confirmed"
        - created_timestamp (int): Время создания (мс)
        - updated_timestamp (int): Время обновления (мс)

Пример:
    # Перевести 0.1 BTC из funding в option
    result = await transfer(
        client,
        currency="BTC",
        amount=0.1,
        destination="option",
        source="funding"
    )
    print(f"Transfer {result['id']} confirmed")
"""

from utils.logger import logger
from utils.timer import timed_execution


# Допустимые типы кошельков
VALID_WALLETS = {"funding", "spot", "future", "option"}


@timed_execution
async def transfer(
    client,
    currency: str,
    amount: float,
    destination: str,
    source: str,
) -> dict:
    """
    Выполнение внутреннего перевода между кошельками Deribit.

    Args:
        client: Экземпляр DeribitClient
        currency: "BTC" или "ETH"
        amount: Сумма перевода
        destination: Кошелёк назначения — "funding", "spot", "future", "option"
        source: Кошелёк источника — "funding", "spot", "future", "option"

    Returns:
        dict с данными перевода

    Raises:
        ValueError: Если currency, source или destination невалидны
        Exception: При ошибке запроса к API
    """
    # Валидация
    if currency not in ("BTC", "ETH"):
        raise ValueError(
            f"Неподдерживаемая валюта: {currency}. "
            f"Используйте 'BTC' или 'ETH'"
        )
    if source not in VALID_WALLETS:
        raise ValueError(
            f"Неподдерживаемый источник: {source}. "
            f"Допустимые: {VALID_WALLETS}"
        )
    if destination not in VALID_WALLETS:
        raise ValueError(
            f"Неподдерживаемое назначение: {destination}. "
            f"Допустимые: {VALID_WALLETS}"
        )
    if source == destination:
        raise ValueError(
            f"Источник и назначение совпадают: {source}"
        )
    if amount <= 0:
        raise ValueError(f"Сумма должна быть положительной: {amount}")

    logger.info(
        f"Перевод: {amount} {currency} | "
        f"{source} → {destination}"
    )

    result = await client.call_private(
        method="private/transfer",
        params={
            "currency": currency,
            "amount": amount,
            "destination": destination,
            "source": source,
        }
    )

    transfer_data = result

    transfer = {
        "id": transfer_data.get("id"),
        "currency": transfer_data.get("currency"),
        "amount": transfer_data.get("amount"),
        "source": transfer_data.get("source"),
        "destination": transfer_data.get("destination"),
        "state": transfer_data.get("state"),
        "created_timestamp": transfer_data.get("created_timestamp"),
        "updated_timestamp": transfer_data.get("updated_timestamp"),
    }

    logger.info(
        f"Перевод выполнен: {transfer['id']} | "
        f"{transfer['amount']} {transfer['currency']} | "
        f"{transfer['source']} → {transfer['destination']} | "
        f"state={transfer['state']}"
    )

    return transfer


@timed_execution
async def get_transfers(
    client,
    currency: str = "BTC",
    count: int = 10,
    offset: int = 0,
) -> list:
    """
    Получение истории внутренних переводов.

    API: private/get_transfers
    Документация: https://docs.deribit.com/api-reference/wallet/private-get_transfers

    Args:
        client: Экземпляр DeribitClient
        currency: "BTC" или "ETH"
        count: Количество записей (макс 1000)
        offset: Смещение для пагинации

    Returns:
        list[dict] с данными переводов

    Raises:
        ValueError: Если currency невалидна или count > 1000
        Exception: При ошибке запроса к API
    """
    if currency not in ("BTC", "ETH"):
        raise ValueError(
            f"Неподдерживаемая валюта: {currency}. "
            f"Используйте 'BTC' или 'ETH'"
        )
    if count > 1000:
        raise ValueError(f"Максимальное количество записей: 1000. Получено: {count}")

    logger.info(
        f"Запрос истории переводов: {currency} | "
        f"count={count} | offset={offset}"
    )

    result = await client.call_private(
        method="private/get_transfers",
        params={
            "currency": currency,
            "count": count,
            "offset": offset,
        }
    )

    transfers = []
    for item in result:
        transfers.append({
            "id": item.get("id"),
            "currency": item.get("currency"),
            "amount": item.get("amount"),
            "source": item.get("source"),
            "destination": item.get("destination"),
            "state": item.get("state"),
            "created_timestamp": item.get("created_timestamp"),
            "updated_timestamp": item.get("updated_timestamp"),
        })

    logger.info(
        f"Получено переводов: {len(transfers)} | "
        f"currency={currency} | offset={offset}"
    )

    return transfers
