"""
Установка тейк-профита и стоп-лосса для позиции Deribit.

API: private/buy или private/sell (создание стоп-ордера)
Документация: https://docs.deribit.com/api-reference/trading/private-buy

Примечание:
    Deribit НЕ имеет отдельного endpoint для TP/SL как Bybit (v5/position/trading-stop).
    Стоп-лосс и тейк-профит реализуются через создание отдельных стоп-ордеров:
      - Стоп-лосс: стоп-ордер в направлении, закрывающем позицию
      - Тейк-профит: лимитный ордер в направлении, закрывающем позицию

    Эта функция создаёт стоп-ордер для управления рисками позиции.

Параметры:
    client (DeribitClient): Экземпляр Deribit клиента
    instrument_name (str): Название инструмента позиции
    side (str): Направление стоп-ордера — "buy" или "sell"
    amount (float): Количество контрактов
    stop_price (float, optional): Цена активации стоп-ордера
    take_profit_price (float, optional): Цена тейк-профита (лимитный ордер)
    order_type (str): Тип стоп-ордера — "stop" или "stop_limit"
    label (str, optional): Метка ордера

Возвращает:
    dict:
        - stop_order_id (str): ID стоп-ордера (если создан)
        - tp_order_id (str): ID тейк-профит ордера (если создан)
        - stop_price (float): Цена активации стопа
        - take_profit_price (float): Цена тейк-профита
        - instrument_name (str): Название инструмента
        - amount (float): Объём

Пример:
    # Установить только стоп-лосс
    result = await take_stop(
        client,
        instrument_name="BTC-27DEC24-80000-C",
        side="sell",  # Закрываем длинную позицию продажей
        amount=1,
        stop_price=1000  # Стоп-лосс при 1000
    )

    # Установить и стоп-лосс, и тейк-профит
    result = await take_stop(
        client,
        instrument_name="BTC-27DEC24-80000-C",
        side="sell",
        amount=1,
        stop_price=1000,
        take_profit_price=2000
    )
    print(f"Stop order: {result['stop_order_id']}, TP order: {result['tp_order_id']}")
"""

from utils.logger import logger
from utils.timer import timed_execution


@timed_execution
async def take_stop(
    client,
    instrument_name: str,
    side: str,
    amount: float,
    stop_price: float = None,
    take_profit_price: float = None,
    order_type: str = "stop",
    label: str = None,
) -> dict:
    """
    Установка стоп-лосса и/или тейк-профита через создание стоп-ордеров.

    Args:
        client: Экземпляр DeribitClient
        instrument_name: Название инструмента позиции
        side: Направление закрывающего ордера ("buy" или "sell")
        amount: Количество контрактов
        stop_price: Цена активации стоп-лосса
        take_profit_price: Цена тейк-профита
        order_type: Тип стоп-ордера — "stop" или "stop_limit"
        label: Метка ордера

    Returns:
        dict с ID созданных ордеров

    Raises:
        ValueError: Если не указан ни stop_price, ни take_profit_price
        Exception: При ошибке запроса к API
    """
    if stop_price is None and take_profit_price is None:
        raise ValueError(
            "Необходимо указать хотя бы один параметр: "
            "stop_price или take_profit_price"
        )

    if side not in ("buy", "sell"):
        raise ValueError(f"Неподдерживаемая сторона: {side}. Используйте 'buy' или 'sell'")

    result = {
        "instrument_name": instrument_name,
        "side": side,
        "amount": amount,
        "stop_order_id": None,
        "tp_order_id": None,
        "stop_price": stop_price,
        "take_profit_price": take_profit_price,
    }

    # ─── Создаём стоп-лосс ордер ──────────────────────────────────
    if stop_price is not None:
        sl_method = "private/buy" if side == "buy" else "private/sell"
        sl_params = {
            "instrument_name": instrument_name,
            "amount": amount,
            "type": order_type,
            "trigger_price": stop_price,
            "reduce_only": True,
            "label": label or "SL",
        }

        logger.info(
            f"Создание стоп-лосса: {instrument_name} | "
            f"side={side} | trigger={stop_price} | amount={amount}"
        )

        sl_result = await client.call_private(method=sl_method, params=sl_params)
        result["stop_order_id"] = sl_result.get("order", {}).get("order_id")

        logger.info(f"Стоп-лосс ордер создан: {result['stop_order_id']}")

    # ─── Создаём тейк-профит ордер ────────────────────────────────
    if take_profit_price is not None:
        tp_method = "private/buy" if side == "buy" else "private/sell"
        tp_params = {
            "instrument_name": instrument_name,
            "amount": amount,
            "type": "limit",
            "price": take_profit_price,
            "reduce_only": True,
            "post_only": True,
            "label": label or "TP",
        }

        logger.info(
            f"Создание тейк-профита: {instrument_name} | "
            f"side={side} | price={take_profit_price} | amount={amount}"
        )

        tp_result = await client.call_private(method=tp_method, params=tp_params)
        result["tp_order_id"] = tp_result.get("order", {}).get("order_id")

        logger.info(f"Тейк-профит ордер создан: {result['tp_order_id']}")

    return result
