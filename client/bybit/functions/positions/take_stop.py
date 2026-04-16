"""
Установка тейк-профита и стоп-лосса для позиции Bybit.

API: POST /v5/position/trading-stop
Документация: https://bybit-exchange.github.io/docs/v5/position/trading-stop

Для опционов используется category="option".

Параметры:
    client (BybitClient): Экземпляр Bybit клиента
    symbol (str): Символ инструмента
    take_profit (str, optional): Цена тейк-профита
    stop_loss (str, optional): Цена стоп-лосса
    trailing_stop (str, optional): Трейлинг стоп (расстояние от лучшей цены)
    tp_trigger_by (str, optional): Триггер TP — "LastPrice", "IndexPrice", "MarkPrice"
    sl_trigger_by (str, optional): Триггер SL — "LastPrice", "IndexPrice", "MarkPrice"
    active_price (str, optional): Активная цена для трейлинг стопа
    tp_size (str, optional): Размер TP ордера
    sl_size (str, optional): Размер SL ордера
    tp_limit_price (str, optional): Лимитная цена TP
    sl_limit_price (str, optional): Лимитная цена SL
    tpsl_mode (str, optional): Режим — "Full" (полный) или "Partial" (частичный)

Возвращает:
    dict:
        - symbol (str): Символ инструмента
        - take_profit (str): Цена TP
        - stop_loss (str): Цена SL
        - trailing_stop (str): Трейлинг стоп
        - tp_trigger_by (str): Триггер TP
        - sl_trigger_by (str): Триггер SL
        - tpsl_mode (str): Режим TP/SL

Пример:
    # Установить TP и SL
    result = await take_stop(
        client,
        symbol="BTC-27DEC24-80000-C",
        take_profit="2000",
        stop_loss="1000",
        tp_trigger_by="MarkPrice",
        sl_trigger_by="MarkPrice"
    )
    print(f"TP: {result['take_profit']} | SL: {result['stop_loss']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def take_stop(
    client,
    symbol: str,
    take_profit: str = None,
    stop_loss: str = None,
    trailing_stop: str = None,
    tp_trigger_by: str = None,
    sl_trigger_by: str = None,
    active_price: str = None,
    tp_size: str = None,
    sl_size: str = None,
    tp_limit_price: str = None,
    sl_limit_price: str = None,
    tpsl_mode: str = None,
) -> dict:
    """
    Установка TP/SL для позиции.

    Args:
        client: Экземпляр BybitClient
        symbol: Символ инструмента
        take_profit: Цена TP
        stop_loss: Цена SL
        trailing_stop: Трейлинг стоп
        tp_trigger_by: Триггер TP
        sl_trigger_by: Триггер SL
        active_price: Активная цена для трейлинг стопа
        tp_size: Размер TP ордера
        sl_size: Размер SL ордера
        tp_limit_price: Лимитная цена TP
        sl_limit_price: Лимитная цена SL
        tpsl_mode: "Full" или "Partial"

    Returns:
        dict с данными TP/SL

    Raises:
        ValueError: Если не указан ни TP, ни SL, ни trailing_stop
        Exception: При ошибке запроса к API
    """
    if not take_profit and not stop_loss and not trailing_stop:
        raise ValueError(
            "Необходимо указать хотя бы один параметр: "
            "take_profit, stop_loss или trailing_stop"
        )

    params = {
        "category": "option",
        "symbol": symbol,
    }

    if take_profit is not None:
        params["takeProfit"] = take_profit
    if stop_loss is not None:
        params["stopLoss"] = stop_loss
    if trailing_stop is not None:
        params["trailingStop"] = trailing_stop
    if tp_trigger_by is not None:
        params["tpTriggerBy"] = tp_trigger_by
    if sl_trigger_by is not None:
        params["slTriggerBy"] = sl_trigger_by
    if active_price is not None:
        params["activePrice"] = active_price
    if tp_size is not None:
        params["tpSize"] = tp_size
    if sl_size is not None:
        params["slSize"] = sl_size
    if tp_limit_price is not None:
        params["tpLimitPrice"] = tp_limit_price
    if sl_limit_price is not None:
        params["slLimitPrice"] = sl_limit_price
    if tpsl_mode is not None:
        params["tpslMode"] = tpsl_mode

    logger.info(
        f"Установка TP/SL: {symbol} | "
        f"TP={take_profit} | SL={stop_loss} | TS={trailing_stop}"
    )

    result = await client.call_private(
        method="set_trading_stop",
        params=params,
    )

    tp_sl = {
        "symbol": symbol,
        "take_profit": result.get("takeProfit"),
        "stop_loss": result.get("stopLoss"),
        "trailing_stop": result.get("trailingStop"),
        "tp_trigger_by": result.get("tpTriggerBy"),
        "sl_trigger_by": result.get("slTriggerBy"),
        "tpsl_mode": result.get("tpslMode"),
    }

    logger.info(
        f"TP/SL установлены: {symbol} | "
        f"TP={tp_sl['take_profit']} | SL={tp_sl['stop_loss']}"
    )

    return tp_sl
