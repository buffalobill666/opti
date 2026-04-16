"""
Webhook сервер для получения алертов от TradingView.

Запускается на отдельном порту (по умолчанию 80).
Принимает POST запросы от TradingView и выполняет указанные действия.

Endpoints:
    POST /webhook/bybit   — webhook для Bybit
    POST /webhook/deribit — webhook для Deribit
    POST /webhook/auto    — автоматическое определение биржи
    GET  /webhook/health  — проверка здоровья сервера

TradingView настраивается на отправку POST запроса с JSON payload.
"""

import os
import time
from collections import defaultdict

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from webhook.models import TradingViewAlert, WebhookResponse
from webhook.handlers.alert_handler import handle_alert
from utils.logger import logger

# ─── Инициализация приложения ───────────────────────────────────────

app = FastAPI(
    title="OptionsRunner Webhook Server",
    description="Сервер для получения алертов от TradingView",
    version="1.0.0",
)

# ─── Rate Limiting ──────────────────────────────────────────────────

# Хранилище запросов: {ip: [timestamp, ...]}
_request_log: dict[str, list[float]] = defaultdict(list)

# Лимит: 10 запросов в минуту
RATE_LIMIT = 10
RATE_WINDOW = 60  # секунд


def check_rate_limit(client_ip: str) -> bool:
    """
    Проверка rate limiting.

    Args:
        client_ip: IP клиента

    Returns:
        True если запрос разрешён
    """
    now = time.time()
    # Удаляем старые записи
    _request_log[client_ip] = [
        ts for ts in _request_log[client_ip]
        if now - ts < RATE_WINDOW
    ]

    if len(_request_log[client_ip]) >= RATE_LIMIT:
        return False

    _request_log[client_ip].append(now)
    return True


# ─── Валидация секрета ──────────────────────────────────────────────

def validate_webhook_secret(request: Request) -> bool:
    """
    Валидация webhook секрета из заголовка.

    Проверяет заголовок X-Webhook-Secret против WEBHOOK_SECRET.
    Если WEBHOOK_SECRET не установлен — пропускает.

    Args:
        request: FastAPI Request

    Returns:
        True если секрет валиден
    """
    webhook_secret = os.getenv("WEBHOOK_SECRET")
    if not webhook_secret:
        return True  # Секрет не настроен — пропускаем

    header_secret = request.headers.get("X-Webhook-Secret", "")
    return header_secret == webhook_secret


# ─── Endpoints ──────────────────────────────────────────────────────

@app.get("/webhook/health")
async def health_check():
    """Проверка здоровья сервера."""
    return {
        "status": "ok",
        "message": "OptionsRunner Webhook Server is running",
        "rate_limit": f"{RATE_LIMIT} запросов / {RATE_WINDOW}с",
    }


@app.post("/webhook/bybit")
async def webhook_bybit(request: Request):
    """
    Webhook для Bybit.

    TradingView отправляет POST запрос с JSON payload.
    """
    return await process_webhook(request, forced_exchange="bybit")


@app.post("/webhook/deribit")
async def webhook_deribit(request: Request):
    """
    Webhook для Deribit.

    TradingView отправляет POST запрос с JSON payload.
    """
    return await process_webhook(request, forced_exchange="deribit")


@app.post("/webhook/auto")
async def webhook_auto(request: Request):
    """
    Автоматическое определение биржи из данных.

    Биржа указывается в поле "exchange" payload.
    """
    return await process_webhook(request, forced_exchange=None)


async def process_webhook(request: Request, forced_exchange: str = None) -> JSONResponse:
    """
    Общая обработка webhook запроса.

    Args:
        request: FastAPI Request
        forced_exchange: Принудительная биржа (None = авто)

    Returns:
        JSONResponse с результатом
    """
    client_ip = request.client.host if request.client else "unknown"

    # ─── Rate Limiting ──────────────────────────────────────────
    if not check_rate_limit(client_ip):
        logger.warning(f"Rate limit превышен для {client_ip}")
        return JSONResponse(
            status_code=429,
            content={
                "status": "error",
                "message": f"Rate limit exceeded: {RATE_LIMIT} запросов / {RATE_WINDOW}с",
            },
        )

    # ─── Валидация секрета ──────────────────────────────────────
    if not validate_webhook_secret(request):
        logger.warning(f"Неверный webhook секрет от {client_ip}")
        return JSONResponse(
            status_code=403,
            content={
                "status": "error",
                "message": "Invalid webhook secret",
            },
        )

    # ─── Парсинг тела ───────────────────────────────────────────
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"Ошибка парсинга JSON: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": f"Invalid JSON: {str(e)}",
            },
        )

    # ─── Принудительная биржа ───────────────────────────────────
    if forced_exchange:
        body["exchange"] = forced_exchange

    # ─── Валидация модели ───────────────────────────────────────
    try:
        alert = TradingViewAlert(**body)
    except Exception as e:
        logger.error(f"Ошибка валидации алерта: {e} | body={body}")
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": f"Invalid alert format: {str(e)}",
            },
        )

    # ─── Обработка ──────────────────────────────────────────────
    logger.info(
        f"Webhook получен: {alert.exchange} | "
        f"{alert.action} {alert.symbol} | "
        f"ip={client_ip}"
    )

    result = await handle_alert(alert)

    if result.get("status") == "ok":
        return JSONResponse(status_code=200, content=result)
    else:
        return JSONResponse(status_code=500, content=result)


# ─── Примеры payload для TradingView ────────────────────────────────

@app.get("/webhook/examples")
async def webhook_examples():
    """Примеры JSON payload для настройки TradingView."""
    return {
        "buy_limit": {
            "exchange": "bybit",
            "symbol": "BTC-27DEC24-80000-C",
            "action": "buy",
            "order_type": "limit",
            "price": 1500,
            "amount": 1,
            "strategy": "My Strategy",
            "time_in_force": "GTC"
        },
        "sell_market": {
            "exchange": "deribit",
            "symbol": "BTC-27DEC24-80000-C",
            "action": "sell",
            "order_type": "market",
            "amount": 1,
            "strategy": "My Strategy"
        },
        "cancel": {
            "exchange": "bybit",
            "symbol": "BTC-27DEC24-80000-C",
            "action": "cancel",
            "extra": {
                "order_id": "abc123"
            }
        },
        "with_tp_sl": {
            "exchange": "bybit",
            "symbol": "BTC-27DEC24-80000-C",
            "action": "buy",
            "order_type": "limit",
            "price": 1500,
            "amount": 1,
            "stop_loss": 1000,
            "take_profit": 2000,
            "strategy": "TP/SL Strategy"
        }
    }
