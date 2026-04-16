"""
Централизованная конфигурация логирования для OptionsRunner.

Использует loguru для записи логов в 5 файлов:
  - options_runner.log  — все действия (DEBUG+)
  - errors.log          — только ошибки (ERROR+)
  - api_requests.log    — HTTP/WebSocket запросы к биржам
  - webhook.log         — Webhook запросы от TradingView
  - gui_access.log      — Доступ к Web-GUI

Все логи ротируются по размеру и сжимаются по истечении срока хранения.
"""

import sys
from pathlib import Path
from loguru import logger

# ─── Директория логов ───────────────────────────────────────────────
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# ─── Формат ─────────────────────────────────────────────────────────
LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "{message}"
)

# ─── Убираем стандартный вывод (заменим своим) ──────────────────────
logger.remove()

# ─── 1. Основной лог — все действия ─────────────────────────────────
logger.add(
    LOGS_DIR / "options_runner.log",
    format=LOG_FORMAT,
    level="DEBUG",
    rotation="10 MB",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
    enqueue=True,
)

# ─── 2. Только ошибки ───────────────────────────────────────────────
logger.add(
    LOGS_DIR / "errors.log",
    format=LOG_FORMAT,
    level="ERROR",
    rotation="5 MB",
    retention="90 days",
    compression="zip",
    encoding="utf-8",
    enqueue=True,
)

# ─── 3. API запросы к биржам (кратко) ───────────────────────────────
logger.add(
    LOGS_DIR / "api_requests.log",
    format=LOG_FORMAT,
    level="INFO",
    rotation="10 MB",
    retention="14 days",
    compression="zip",
    encoding="utf-8",
    enqueue=False,  # Немедленная запись
    filter=lambda record: record["extra"].get("category") == "api",
)

# ─── 3б. Детальные API запросы (заголовки + тело) ───────────────────
logger.add(
    LOGS_DIR / "api_detail.log",
    format=LOG_FORMAT,
    level="DEBUG",
    rotation="20 MB",
    retention="7 days",
    compression="zip",
    encoding="utf-8",
    enqueue=False,  # Немедленная запись
    filter=lambda record: record["extra"].get("category") == "api_detail",
)

# ─── 4. Webhook запросы ─────────────────────────────────────────────
logger.add(
    LOGS_DIR / "webhook.log",
    format=LOG_FORMAT,
    level="INFO",
    rotation="5 MB",
    retention="14 days",
    compression="zip",
    encoding="utf-8",
    enqueue=True,
    filter=lambda record: record["extra"].get("category") == "webhook",
)

# ─── 5. Доступ к Web-GUI ────────────────────────────────────────────
logger.add(
    LOGS_DIR / "gui_access.log",
    format=LOG_FORMAT,
    level="INFO",
    rotation="5 MB",
    retention="14 days",
    compression="zip",
    encoding="utf-8",
    enqueue=True,
    filter=lambda record: record["extra"].get("category") == "gui",
)

# ─── Консольный вывод ───────────────────────────────────────────────
logger.add(
    sys.stderr,
    format=LOG_FORMAT,
    level="DEBUG",
    colorize=True,
    enqueue=False,
)

# ─── Хелперы для категорий ──────────────────────────────────────────

def log_api_request(exchange: str, method: str, params: dict, elapsed: float, success: bool):
    """
    Логирование API запроса к бирже (кратко).

    Всегда логирует — и успех, и ошибку.
    """
    status = "OK" if success else "FAIL"
    log_msg = (
        f"[{exchange.upper()}] {method} | "
        f"params={params} | "
        f"[{status}] | "
        f"{elapsed:.3f}s"
    )
    if success:
        logger.bind(category="api").info(log_msg)
    else:
        logger.bind(category="api").error(log_msg)


def log_api_request_detail(
    exchange: str,
    method: str,
    url: str,
    headers: dict,
    body: dict,
    response_status: int,
    response_body: dict,
    elapsed: float,
    success: bool,
    api_key: str = None,
    signature: str = None,
):
    """
    Детальное логирование API запроса с заголовками и телом.

    Args:
        exchange: "bybit" или "deribit"
        method: HTTP метод или имя метода API
        url: URL запроса
        headers: Заголовки запроса
        body: Тело запроса
        response_status: HTTP статус ответа
        response_body: Тело ответа
        elapsed: Время выполнения (сек)
        success: Успешность запроса
        api_key: API ключ (для логирования)
        signature: Подпись запроса (для логирования)
    """
    # Маскируем секреты в заголовках
    safe_headers = {}
    for k, v in headers.items():
        kl = k.lower()
        if "secret" in kl or "sign" in kl or "token" in kl:
            safe_headers[k] = v[:12] + "****" if v and len(v) > 12 else "****"
        elif "key" in kl or "auth" in kl:
            safe_headers[k] = v[:8] + "****" if v and len(v) > 8 else "****"
        else:
            safe_headers[k] = v

    # Добавляем API ключ и подпись если есть
    extra_info = ""
    if api_key:
        extra_info += f"\nAPI Key: {api_key}"
    if signature:
        extra_info += f"\nSignature: {signature[:40]}****"

    # Формируем сообщение
    lines = [
        f"{'='*80}",
        f"[{exchange.upper()}] {method} | {elapsed:.3f}s | {'OK' if success else 'FAIL'}",
        f"{'='*80}",
        f"URL:     {url}",
        f"Headers: {safe_headers}",
        f"Body:    {body}",
        f"Status:  {response_status}",
        f"Response: {response_body}",
        f"{'='*80}",
    ]
    if extra_info:
        lines.insert(3, extra_info.strip())
    detail_msg = "\n".join(lines)

    if success:
        logger.bind(category="api_detail").debug(detail_msg)
    else:
        logger.bind(category="api_detail").error(detail_msg)


def log_webhook(exchange: str, action: str, symbol: str, elapsed: float, status: str = "OK"):
    """Логирование webhook запроса."""
    logger.bind(category="webhook").info(
        f"[{exchange.upper()}] {action} | "
        f"symbol={symbol} | "
        f"[{status}] | "
        f"{elapsed:.3f}s"
    )


def log_gui_access(user: str, ip: str, path: str):
    """Логирование доступа к Web-GUI."""
    logger.bind(category="gui").info(
        f"user={user} | ip={ip} | path={path}"
    )
