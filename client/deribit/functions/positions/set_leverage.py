"""
Управление маржой позиции Deribit.

API: private/set_margins (для изменения размера маржи)
Документация: https://docs.deribit.com/api-reference/account-management/private-set_margins

Примечание:
    Deribit НЕ использует концепцию "leverage" (кредитного плеча) как Bybit.
    Вместо этого — ручное управление маржой для позиций.
    Для опционов Deribit использует портфельную маржу, которая рассчитывается
    автоматически на основе риска портфеля.

    Эта функция-заглушка информирует о специфике Deribit.
    Для реального изменения маржи используйте private/set_margins.

Параметры:
    client (DeribitClient): Экземпляр Deribit клиента
    currency (str): Валюта — "BTC" или "ETH"
    margin (float, optional): Желаемый размер маржи

Возвращает:
    dict:
        - supported (bool): False — функция не применима для опционов Deribit
        - message (str): Пояснение о специфике Deribit
        - alternative (str): Рекомендуемый альтернативный метод

Пример:
    result = await set_leverage(client, currency="BTC", margin=0.5)
    print(result['message'])
    # "Deribit не использует leverage. Используйте ручное управление маржой."
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def set_leverage(
    client,
    currency: str,
    margin: float = None
) -> dict:
    """
    Заглушка для установки кредитного плеча.

    Deribit не поддерживает концепцию leverage для опционов.
    Маржа рассчитывается автоматически на основе портфельного риска.

    Args:
        client: Экземпляр DeribitClient
        currency: "BTC" или "ETH"
        margin: Желаемый размер маржи (опционально)

    Returns:
        dict с пояснением и альтернативным методом
    """
    logger.warning(
        f"set_leverage вызвана для {currency} — "
        f"Deribit не использует leverage для опционов"
    )

    return {
        "supported": False,
        "message": (
            "Deribit не использует концепцию 'leverage' (кредитного плеча) "
            "для опционов. Маржа рассчитывается автоматически на основе "
            "портфельного риска (Portfolio Margin)."
        ),
        "alternative": (
            "Для управления маржой используйте: "
            "1. private/set_margins — ручная установка маржи "
            "2. private/get_account_summary — просмотр текущей маржи"
        ),
        "currency": currency,
        "requested_margin": margin,
    }


async def set_margins(client, currency: str, margin: float) -> dict:
    """
    Ручная установка размера маржи для указанной валюты.

    Args:
        client: Экземпляр DeribitClient
        currency: "BTC" или "ETH"
        margin: Желаемый размер маржи

    Returns:
        dict с обновлёнными данными маржи
    """
    if currency not in ("BTC", "ETH"):
        raise ValueError(
            f"Неподдерживаемая валюта: {currency}. "
            f"Используйте 'BTC' или 'ETH'"
        )

    logger.info(
        f"Установка маржи: {currency} = {margin}"
    )

    result = await client.call_private(
        method="private/set_margins",
        params={
            "currency": currency,
            "margin": margin,
        }
    )

    margins = {
        "currency": currency,
        "margin": margin,
        "margin_balance": result.get("margin_balance"),
        "available_funds": result.get("available_funds"),
        "initial_margin": result.get("initial_margin"),
        "maintenance_margin": result.get("maintenance_margin"),
    }

    logger.info(
        f"Маржа установлена: {currency} = {margin} | "
        f"available={margins['available_funds']}"
    )

    return margins
