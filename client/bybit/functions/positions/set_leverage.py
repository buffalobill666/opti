"""
Установка кредитного плеча для позиции Bybit.

API: POST /v5/position/set-leverage
Документация: https://bybit-exchange.github.io/docs/v5/position/leverage

Для опционов используется category="option".

Примечание:
    Опционы Bybit используют портфельную маржу (Portfolio Margin).
    Кредитное плечо для опционов не применяется напрямую —
    маржа рассчитывается автоматически на основе риска портфеля.

    Эта функция-заглушка информирует о специфике Bybit Options.

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    symbol (str): Символ инструмента
    buy_leverage (float): Плечо для длинных позиций
    sell_leverage (float): Плечо для коротких позиций

Возвращает:
    dict:
        - supported (bool): False — функция не применима для опционов
        - message (str): Пояснение о специфике Bybit Options
        - alternative (str): Рекомендуемый альтернативный метод

Пример:
    result = await set_leverage(client, symbol="BTC-27DEC24-80000-C",
                                buy_leverage=5, sell_leverage=5)
    print(result['message'])
    # "Опционы Bybit используют портфельную маржу."
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def set_leverage(
    client,
    symbol: str,
    buy_leverage: float,
    sell_leverage: float,
) -> dict:
    """
    Заглушка для установки кредитного плеча.

    Опционы Bybit не используют leverage напрямую.
    Маржа рассчитывается автоматически через Portfolio Margin.

    Args:
        client: Экземпляр BybitClient
        symbol: Символ инструмента
        buy_leverage: Плечо для длинных позиций
        sell_leverage: Плечо для коротких позиций

    Returns:
        dict с пояснением
    """
    logger.warning(
        f"set_leverage вызвана для {symbol} — "
        f"Bybit Options используют Portfolio Margin"
    )

    return {
        "supported": False,
        "message": (
            "Опционы Bybit используют портфельную маржу (Portfolio Margin). "
            "Кредитное плечо не применяется напрямую к опционам. "
            "Маржа рассчитывается автоматически на основе риска всего портфеля."
        ),
        "alternative": (
            "Для управления риском используйте: "
            "1. get_positions — просмотр текущих позиций и греков "
            "2. set_trading_stop — установка TP/SL "
            "3. create_order с reduceOnly=True — закрытие позиций"
        ),
        "symbol": symbol,
        "requested_buy_leverage": buy_leverage,
        "requested_sell_leverage": sell_leverage,
    }
