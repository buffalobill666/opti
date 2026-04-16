"""
Общий обработчик webhook алертов от TradingView.

Принимает распарсенный алерт, определяет действие
и вызывает соответствующий handler.
"""

import time

from webhook.models import TradingViewAlert
from webhook.handlers.order_handler import handle_order
from webhook.handlers.cancel_handler import handle_cancel
from utils.logger import logger, log_webhook


async def handle_alert(alert: TradingViewAlert) -> dict:
    """
    Основной обработчик алертов.

    Определяет действие и вызывает соответствующий handler.

    Args:
        alert: Распарсенный алерт от TradingView

    Returns:
        dict: Результат выполнения действия
    """
    start_time = time.perf_counter()

    logger.info(
        f"Получен алерт: {alert.exchange} | "
        f"{alert.action} {alert.symbol} | "
        f"strategy={alert.strategy or 'N/A'}"
    )

    try:
        if alert.action in ("buy", "sell"):
            result = await handle_order(alert)

        elif alert.action == "cancel":
            result = await handle_cancel(alert)

        elif alert.action == "amend":
            result = await handle_amend(alert)

        elif alert.action == "close":
            result = await handle_close(alert)

        else:
            logger.warning(f"Неподдерживаемое действие: {alert.action}")
            return {
                "status": "error",
                "message": f"Неподдерживаемое действие: {alert.action}",
            }

        elapsed = time.perf_counter() - start_time

        # Логирование webhook
        log_webhook(
            exchange=alert.exchange,
            action=alert.action,
            symbol=alert.symbol,
            elapsed=elapsed,
            status="ok",
        )

        return result

    except Exception as e:
        elapsed = time.perf_counter() - start_time

        log_webhook(
            exchange=alert.exchange,
            action=alert.action,
            symbol=alert.symbol,
            elapsed=elapsed,
            status="error",
        )

        logger.error(f"Ошибка обработки алерта: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


async def handle_amend(alert: TradingViewAlert) -> dict:
    """
    Обработчик изменения ордера.

    Args:
        alert: Алерт с действием amend

    Returns:
        dict: Результат изменения
    """
    from webhook.handlers.order_handler import handle_order

    # Amend обрабатывается через order_handler с доп. параметрами
    return await handle_order(alert)


async def handle_close(alert: TradingViewAlert) -> dict:
    """
    Обработчик закрытия позиции.

    Создаёт рыночный ордер в противоположном направлении.

    Args:
        alert: Алерт с действием close

    Returns:
        dict: Результат закрытия
    """
    # Определяем противоположную сторону
    side = "sell" if alert.action == "close" else "buy"

    close_alert = TradingViewAlert(
        exchange=alert.exchange,
        symbol=alert.symbol,
        action=side,
        order_type="market",
        amount=alert.amount,
        strategy=f"close_{alert.strategy or 'position'}",
    )

    return await handle_order(close_alert)
