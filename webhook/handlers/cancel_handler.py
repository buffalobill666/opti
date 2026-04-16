"""
Обработчик отмены ордеров от webhook TradingView.

Отменяет ордер на бирже через UnifiedClient.
"""

from webhook.models import TradingViewAlert
from ui.key_store import get_decrypted_keys
from utils.logger import logger


async def handle_cancel(alert: TradingViewAlert) -> dict:
    """
    Отмена ордера из webhook.

    Вызывает UnifiedClient.cancel_order().

    Args:
        alert: Алерт от TradingView

    Returns:
        dict: Результат отмены

    Raises:
        Exception: При ошибке отмены
    """
    logger.info(
        f"Отмена ордера: {alert.exchange} | "
        f"symbol={alert.symbol} | "
        f"extra={alert.extra}"
    )

    # Получаем ключи
    keys = get_decrypted_keys(alert.exchange)
    if not keys:
        raise Exception(f"API ключи для {alert.exchange} не настроены")

    from client.main_client import UnifiedClient

    client = UnifiedClient()

    # ID ордера может быть в extra или в symbol
    order_id = None
    if alert.extra and "order_id" in alert.extra:
        order_id = alert.extra["order_id"]
    elif alert.extra and "order_link_id" in alert.extra:
        order_id = alert.extra["order_link_id"]

    if not order_id:
        raise Exception("order_id не указан в алерте (укажите в extra.order_id)")

    if alert.exchange == "bybit":
        client.init_bybit(
            api_key=keys["api_key"],
            api_secret=keys["api_secret"],
            testnet=keys["testnet"],
        )

        result = await client.cancel_order(
            "bybit",
            symbol=alert.symbol,
            order_id=order_id,
        )

        return {
            "status": "ok",
            "message": f"Ордер отменён на Bybit: {order_id}",
            "order_id": order_id,
            "exchange": "bybit",
            "action": "cancel",
        }

    elif alert.exchange == "deribit":
        client.init_deribit(
            client_id=keys["api_key"],
            client_secret=keys["api_secret"],
            testnet=keys["testnet"],
        )

        result = await client.cancel_order(
            "deribit",
            order_id=order_id,
        )

        return {
            "status": "ok",
            "message": f"Ордер отменён на Deribit: {order_id}",
            "order_id": order_id,
            "exchange": "deribit",
            "action": "cancel",
        }

    else:
        raise Exception(f"Неподдерживаемая биржа: {alert.exchange}")
