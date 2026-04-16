"""
Точка входа для запуска всех сервисов OptionsRunner.

Запускает параллельно:
  1. Web-GUI (FastAPI) — интерфейс для управления торговлей
  2. Webhook сервер (FastAPI) — получение алертов от TradingView

Использование:
    python main.py

Переменные окружения (.env):
    WEB_HOST      — хост Web-GUI (по умолчанию 0.0.0.0)
    WEB_PORT      — порт Web-GUI (по умолчанию 8000)
    WEBHOOK_PORT  — порт Webhook сервера (по умолчанию 5000)
    ADMIN_PASSWORD — пароль для входа в Web-GUI
    APP_SECRET_KEY — секретный ключ для сессий
"""

import os
import sys
import signal
import asyncio
import multiprocessing
from pathlib import Path

from dotenv import load_dotenv

from utils.logger import logger

# ─── Загрузка переменных окружения ──────────────────────────────────

load_dotenv()

# ─── Проверка обязательных переменных ───────────────────────────────

REQUIRED_VARS = ["APP_SECRET_KEY", "ADMIN_PASSWORD"]

for var in REQUIRED_VARS:
    if not os.getenv(var):
        logger.error(f"Переменная окружения {var} не установлена!")
        print(f"\n❌ ОШИБКА: Переменная {var} не установлена в .env файле!")
        print("   Скопируйте .env.example в .env и заполните значения.\n")
        sys.exit(1)

# ─── Конфигурация ──────────────────────────────────────────────────

WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "5000"))

# ─── Функции запуска серверов ──────────────────────────────────────


def run_gui(host: str, port: int):
    """
    Запуск Web-GUI сервера.

    Args:
        host: Хост для привязки
        port: Порт для прослушивания
    """
    import uvicorn
    from ui.app import app

    logger.info(f"Запуск Web-GUI на {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=False,  # Логируем через middleware
    )


def run_webhook(host: str, port: int):
    """
    Запуск Webhook сервера.

    Args:
        host: Хост для привязки
        port: Порт для прослушивания
    """
    import uvicorn
    from webhook.webhook_server import app

    logger.info(f"Запуск Webhook сервера на {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )


# ─── Graceful Shutdown ─────────────────────────────────────────────

_processes = []


def signal_handler(signum, frame):
    """
    Обработчик сигналов SIGINT/SIGTERM.
    Корректно завершает все дочерние процессы.
    """
    sig_name = "SIGINT" if signum == signal.SIGINT else "SIGTERM"
    logger.info(f"Получен сигнал {sig_name}, завершение работы...")

    for proc in _processes:
        if proc.is_alive():
            logger.info(f"Остановка процесса: {proc.name}")
            proc.terminate()

    for proc in _processes:
        proc.join(timeout=5)
        if proc.is_alive():
            logger.warning(f"Принудительное завершение: {proc.name}")
            proc.kill()

    logger.info("Все процессы остановлены. Выход.")
    sys.exit(0)


# ─── Async инициализация WebSocket ──────────────────────────────

async def init_websockets(unified_client):
    """Подключение WebSocket клиентов."""
    if unified_client.bybit_ws and not unified_client.bybit_ws.is_connected_public:
        try:
            await unified_client.bybit_ws.connect_public()
            logger.info("Bybit WebSocket (public) подключён")
        except Exception as e:
            logger.warning(f"Bybit WebSocket не подключился: {e}")

    if unified_client.deribit_ws and not unified_client.deribit_ws.is_connected:
        try:
            await unified_client.deribit_ws.connect()
            logger.info("Deribit WebSocket подключён")
        except Exception as e:
            logger.warning(f"Deribit WebSocket не подключился: {e}")


# ─── Основная функция ──────────────────────────────────────────────

def main():
    """
    Основная функция запуска.

    Инициализирует UnifiedClient и запускает оба сервера
    в отдельных процессах.
    """
    # ─── Регистрация обработчиков сигналов ──────────────────────
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # ─── Инициализация UnifiedClient ────────────────────────────
    from client.main_client import UnifiedClient

    unified_client = UnifiedClient()

    # Автоинициализация из сохранённых ключей
    from ui.key_store import get_decrypted_keys

    # Определяем режимы из .env
    bybit_testnet = os.getenv("BYBIT_TESTNET", "false").lower() == "true"
    bybit_demo = os.getenv("BYBIT_DEMO", "false").lower() == "true"
    deribit_testnet = os.getenv("DERIBIT_TESTNET", "false").lower() == "true"

    # Bybit
    if bybit_demo:
        # Demo Trading — читаем из .env напрямую
        demo_key = os.getenv("BYBIT_DEMO_API_KEY", "")
        demo_secret = os.getenv("BYBIT_DEMO_API_SECRET", "")
        if demo_key and demo_secret:
            try:
                unified_client.init_bybit(
                    api_key=demo_key,
                    api_secret=demo_secret,
                    testnet=False,
                    demo=True,
                )
                logger.info("BYBIT клиент инициализирован (demo)")
            except Exception as e:
                logger.warning(f"Не удалось инициализировать Bybit Demo: {e}")
    else:
        bybit_keys = get_decrypted_keys("bybit", testnet=bybit_testnet)
        if bybit_keys:
            try:
                unified_client.init_bybit(
                    api_key=bybit_keys["api_key"],
                    api_secret=bybit_keys["api_secret"],
                    testnet=bybit_testnet,
                )
                mode = "testnet" if bybit_testnet else "mainnet"
                logger.info(f"BYBIT клиент инициализирован ({mode})")
            except Exception as e:
                logger.warning(f"Не удалось инициализировать Bybit: {e}")

    # Deribit
    deribit_keys = get_decrypted_keys("deribit", testnet=deribit_testnet)
    if deribit_keys:
        try:
            unified_client.init_deribit(
                client_id=deribit_keys["api_key"],
                client_secret=deribit_keys["api_secret"],
                testnet=deribit_testnet,
            )
            logger.info(
                f"DERIBIT клиент инициализирован ({'testnet' if deribit_testnet else 'mainnet'})"
            )
        except Exception as e:
            logger.warning(f"Не удалось инициализировать Deribit: {e}")

    # ─── Подключение WebSocket ──────────────────────────────────
    try:
        asyncio.run(init_websockets(unified_client))
    except Exception as e:
        logger.warning(f"Ошибка инициализации WebSocket: {e}")

    # ─── Запуск серверов ────────────────────────────────────────
    gui_process = multiprocessing.Process(
        target=run_gui,
        args=(WEB_HOST, WEB_PORT),
        name="WebGUI",
        daemon=True,
    )

    webhook_process = multiprocessing.Process(
        target=run_webhook,
        args=(WEB_HOST, WEBHOOK_PORT),
        name="Webhook",
        daemon=True,
    )

    _processes.extend([gui_process, webhook_process])

    gui_process.start()
    webhook_process.start()

    # ─── Вывод информации ───────────────────────────────────────
    print()
    print("=" * 60)
    print("  ⚡ OptionsRunner запущен")
    print("=" * 60)
    print()
    print(f"  Web-GUI:   http://localhost:{WEB_PORT}")
    print(f"  Webhook:   http://localhost:{WEBHOOK_PORT}")
    print(f"  Webhook examples: http://localhost:{WEBHOOK_PORT}/webhook/examples")
    print()
    print(f"  Bybit:   {unified_client.get_current_network('bybit') if unified_client.bybit_client else 'not configured'}")
    print(f"  Deribit: {unified_client.get_current_network('deribit') if unified_client.deribit_client else 'not configured'}")
    print()
    print("  Нажмите Ctrl+C для остановки")
    print("=" * 60)
    print()

    logger.info(
        f"OptionsRunner запущен | "
        f"GUI={WEB_PORT} | Webhook={WEBHOOK_PORT}"
    )

    # Ожидание завершения процессов
    try:
        gui_process.join()
        webhook_process.join()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)


if __name__ == "__main__":
    main()
