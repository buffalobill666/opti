"""
Отмена всех активных ордеров на Deribit.

API: private/cancel_all
Документация: https://docs.deribit.com/api-reference/trading/private-cancel_all

Параметры:
    client (DeribitClient): Экземпляр Deribit клиента
    type (str, optional): Тип ордеров для отмены —
        "all" (все), "limit" (только лимитные),
        "stop" (только стоп-ордера), "advanced" (только advanced)

Возвращает:
    dict:
        - cancelled_count (int): Количество отменённых ордеров
        - type (str): Тип отменённых ордеров

Пример:
    result = await cancel_all_orders(client, type="all")
    print(f"Отменено ордеров: {result['cancelled_count']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def cancel_all_orders(
    client,
    type: str = "all",
) -> dict:
    """
    Отмена всех активных ордеров.

    Args:
        client: Экземпляр DeribitClient
        type: Тип ордеров — "all", "limit", "stop", "advanced"

    Returns:
        dict с результатами

    Raises:
        ValueError: Если type невалиден
        Exception: При ошибке запроса к API
    """
    valid_types = {"all", "limit", "stop", "advanced"}
    if type not in valid_types:
        raise ValueError(
            f"Неподдерживаемый тип: {type}. "
            f"Допустимые: {valid_types}"
        )

    params = {"type": type}

    logger.info(f"Отмена всех ордеров: type={type}")

    result = await client.call_private(
        method="private/cancel_all",
        params=params,
    )

    cancelled_count = len(result) if isinstance(result, list) else 0

    logger.info(f"Отмена всех ордеров завершена: отменено={cancelled_count}")

    return {
        "cancelled_count": cancelled_count,
        "type": type,
    }
