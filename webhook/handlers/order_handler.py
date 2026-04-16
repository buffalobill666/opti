"""
Обработчик ордеров от webhook TradingView.

Создаёт ордер на бирже через UnifiedClient.
"""

from webhook.models import TradingViewAlert
from ui.key_store import get_decrypted_keys
from utils.logger import logger


async def handle_order(alert: TradingViewAlert) -> dict:
    """
    Создание ордера из webhook.

    Вызывает UnifiedClient.create_order() с параметрами из алерта.

    Args:
        alert: Алерт от TradingView

    Returns:
        dict: Результат создания ордера

    Raises:
        Exception: При ошибке создания ордера
    """
    logger.info(
        f"Создание ордера: {alert.exchange} | "
        f"{alert.action} {alert.symbol} | "
        f"type={alert.order_type} | qty={alert.amount} | price={alert.price}"
    )

    # Получаем ключи
    keys = get_decrypted_keys(alert.exchange)
    if not keys:
        raise Exception(f"API ключи для {alert.exchange} не настроены")

    from client.main_client import UnifiedClient

    client = UnifiedClient()

    if alert.exchange == "bybit":
        client.init_bybit(
            api_key=keys["api_key"],
            api_secret=keys["api_secret"],
            testnet=keys["testnet"],
        )

        # Bybit параметры
        side = "Buy" if alert.action == "buy" else "Sell"
        order_type = "Limit" if alert.order_type == "limit" else "Market"

        order_kwargs = {
            "symbol": alert.symbol,
            "side": side,
            "order_type": order_type,
            "qty": str(alert.amount),
            "time_in_force": alert.time_in_force or "GTC",
        }

        if alert.price is not None:
            order_kwargs["price"] = str(alert.price)

        result = await client.create_order("bybit", **order_kwargs)

        # Если есть TP/SL — устанавливаем
        if alert.stop_loss or alert.take_profit:
            try:
                await client.set_take_stop(
                    "bybit",
                    symbol=alert.symbol,
                    take_profit=str(alert.take_profit) if alert.take_profit else None,
                    stop_loss=str(alert.stop_loss) if alert.stop_loss else None,
                )
            except Exception as e:
                logger.warning(f"Не удалось установить TP/SL: {e}")

        return {
            "status": "ok",
            "message": f"Ордер создан на Bybit: {result.get('order_id')}",
            "order_id": result.get("order_id"),
            "exchange": "bybit",
            "action": alert.action,
        }

    elif alert.exchange == "deribit":
        client.init_deribit(
            client_id=keys["api_key"],
            client_secret=keys["api_secret"],
            testnet=keys["testnet"],
        )

        # Deribit параметры
        order_kwargs = {
            "instrument_name": alert.symbol,
            "side": alert.action,  # "buy" или "sell"
            "amount": alert.amount,
            "type": alert.order_type or "limit",
            "time_in_force": alert.time_in_force or "good_til_cancelled",
        }

        if alert.price is not None:
            order_kwargs["price"] = alert.price

        result = await client.create_order("deribit", **order_kwargs)

        return {
            "status": "ok",
            "message": f"Ордер создан на Deribit: {result.get('order_id')}",
            "order_id": result.get("order_id"),
            "exchange": "deribit",
            "action": alert.action,
        }

    else:
        raise Exception(f"Неподдерживаемая биржа: {alert.exchange}")
