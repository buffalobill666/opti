"""
WebSocket клиент для получения данных Bybit в реальном времени.

Использует pybit SDK для WebSocket подключений.

URL-адреса:
    Mainnet WS: wss://stream.bybit.com/v5/public
    Testnet WS: wss://stream-testnet.bybit.com/v5/public

Документация:
    WebSocket Overview: https://bybit-exchange.github.io/docs/v5/ws/connect
    pybit SDK: https://github.com/bybit-exchange/pybit

Публичные каналы (category=option):
    - orderbook.{depth}.{symbol}     — стакан
      Пример: orderbook.1.BTC-27DEC24-80000-C
    - publicTrade.{symbol}           — сделки
      Пример: publicTrade.BTC-27DEC24-80000-C
    - tickers.{symbol}               — тикеры
      Пример: tickers.BTC-27DEC24-80000-C
    - kline.{interval}.{symbol}      — свечи
      Пример: kline.60.BTC-27DEC24-80000-C

Приватные каналы:
    - position                       — обновления позиций
    - order                          — обновления ордеров
    - wallet                         — обновления кошелька
"""

import asyncio
import json
from typing import Optional, Callable

from pybit.unified_trading import WebSocket

from utils.logger import logger, log_api_request
from utils.timer import timed_execution


class BybitWebSocketClient:
    """
    WebSocket клиент для получения данных Bybit в реальном времени.

    Использует pybit WebSocket для подписки на потоки данных.
    Поддерживает публичные и приватные каналы.

    Пример использования:
        ws = BybitWebSocketClient(
            api_key="your_api_key",
            api_secret="your_api_secret",
            testnet=True
        )

        def handle_orderbook(data):
            print(f"Orderbook: {data}")

        await ws.connect_public(
            topic="orderbook.1.BTC-27DEC24-80000-C",
            callback=handle_orderbook
        )
    """

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = False,
    ):
        """
        Инициализация WebSocket клиента.

        Args:
            api_key: API ключ (для приватных каналов)
            api_secret: API секрет (для приватных каналов)
            testnet: Использовать тестовую сеть
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet

        # WebSocket сессии
        self._public_ws: Optional[WebSocket] = None
        self._private_ws: Optional[WebSocket] = None

        # Callback-и: {topic: callback_function}
        self.callbacks: dict[str, Callable] = {}

        # Подписки: {topic: callback} — для восстановления
        self._subscriptions: dict[str, Callable] = {}

        # Состояние
        self._connected_public = False
        self._connected_private = False

        network = "testnet" if testnet else "mainnet"
        logger.info(
            f"BybitWebSocketClient инициализирован | "
            f"network={network}"
        )

    # ─── Подключение ────────────────────────────────────────────────

    @timed_execution
    async def connect_public(self) -> bool:
        """
        Подключение к публичному WebSocket.

        Returns:
            True при успешном подключении
        """
        if self._connected_public and self._public_ws:
            logger.debug("Публичный WebSocket уже подключён")
            return True

        logger.info("Подключение к публичному WebSocket")

        try:
            self._public_ws = WebSocket(
                testnet=self.testnet,
                channel_type="public",
            )
            self._connected_public = True

            logger.info("Публичный WebSocket подключён")
            return True

        except Exception as e:
            logger.error(f"Ошибка подключения к публичному WS: {e}")
            self._connected_public = False
            raise

    @timed_execution
    async def connect_private(self) -> bool:
        """
        Подключение к приватному WebSocket.

        Требует api_key и api_secret.

        Returns:
            True при успешном подключении
        """
        if self._connected_private and self._private_ws:
            logger.debug("Приватный WebSocket уже подключён")
            return True

        if not self.api_key or not self.api_secret:
            raise Exception(
                "Для приватного подключения нужны api_key и api_secret"
            )

        logger.info("Подключение к приватному WebSocket")

        try:
            self._private_ws = WebSocket(
                testnet=self.testnet,
                channel_type="private",
                api_key=self.api_key,
                api_secret=self.api_secret,
            )
            self._connected_private = True

            logger.info("Приватный WebSocket подключён")
            return True

        except Exception as e:
            logger.error(f"Ошибка подключения к приватному WS: {e}")
            self._connected_private = False
            raise

    async def close(self):
        """Закрытие WebSocket соединений."""
        if self._public_ws:
            try:
                self._public_ws.exit()
            except Exception:
                pass
            self._connected_public = False

        if self._private_ws:
            try:
                self._private_ws.exit()
            except Exception:
                pass
            self._connected_private = False

        logger.info("WebSocket соединения закрыты")

    # ─── Подписка на публичный канал ────────────────────────────────

    @timed_execution
    async def subscribe_public(
        self,
        topic: str,
        callback: Callable
    ) -> bool:
        """
        Подписка на публичный канал.

        Каналы для опционов (category=option):
            - orderbook.{depth}.{symbol}  — стакан
              Пример: orderbook.1.BTC-27DEC24-80000-C
            - publicTrade.{symbol}        — сделки
              Пример: publicTrade.BTC-27DEC24-80000-C
            - tickers.{symbol}            — тикеры
              Пример: tickers.BTC-27DEC24-80000-C
            - kline.{interval}.{symbol}   — свечи
              Пример: kline.60.BTC-27DEC24-80000-C

        Args:
            topic: Имя топика
            callback: Функция для обработки данных

        Returns:
            True при успешной подписке
        """
        if not self._connected_public:
            await self.connect_public()

        logger.info(f"Подписка на публичный канал: {topic}")

        try:
            self._public_ws.subscribe(
                topic=topic,
                callback=callback,
            )

            self.callbacks[topic] = callback
            self._subscriptions[topic] = callback

            logger.info(f"Подписка успешна: {topic}")
            return True

        except Exception as e:
            logger.error(f"Ошибка подписки на {topic}: {e}")
            raise

    # ─── Подписка на приватный канал ────────────────────────────────

    @timed_execution
    async def subscribe_private(
        self,
        topic: str,
        callback: Callable
    ) -> bool:
        """
        Подписка на приватный канал.

        Каналы:
            - position   — обновления позиций
            - order      — обновления ордеров
            - wallet     — обновления кошелька

        Args:
            topic: Имя топика
            callback: Функция для обработки данных

        Returns:
            True при успешной подписке
        """
        if not self._connected_private:
            await self.connect_private()

        logger.info(f"Подписка на приватный канал: {topic}")

        try:
            self._private_ws.subscribe(
                topic=topic,
                callback=callback,
            )

            self.callbacks[topic] = callback
            self._subscriptions[topic] = callback

            logger.info(f"Подписка успешна: {topic}")
            return True

        except Exception as e:
            logger.error(f"Ошибка подписки на {topic}: {e}")
            raise

    # ─── Отписка ────────────────────────────────────────────────────

    async def unsubscribe(self, topic: str) -> bool:
        """
        Отписка от канала.

        Args:
            topic: Имя топика

        Returns:
            True при успешной отписке
        """
        # Определяем, какой WS использовать
        is_private = topic in ("position", "order", "wallet")
        ws = self._private_ws if is_private else self._public_ws

        if not ws:
            logger.warning(f"Не подключён к WebSocket для {topic}")
            return False

        logger.info(f"Отписка от канала: {topic}")

        try:
            ws.unsubscribe(topic=topic)

            self.callbacks.pop(topic, None)
            self._subscriptions.pop(topic, None)

            logger.info(f"Отписка успешна: {topic}")
            return True

        except Exception as e:
            logger.error(f"Ошибка отписки от {topic}: {e}")
            raise

    # ─── Переключение сети ──────────────────────────────────────────

    def switch_network(self, testnet: bool):
        """
        Переключение между testnet и mainnet.

        Требует переподключения WebSocket.

        Args:
            testnet: True = stream-testnet.bybit.com
        """
        old_network = "mainnet" if not self.testnet else "testnet"
        new_network = "testnet" if testnet else "mainnet"

        self.testnet = testnet

        logger.info(
            f"Bybit WebSocket сеть переключена: "
            f"{old_network} → {new_network}"
        )

        # Закрыть соединения — потребуется переподключение
        if self._connected_public or self._connected_private:
            logger.info("Активные соединения будут переподключены")
            asyncio.create_task(self.close())

    def get_network_url(self) -> str:
        """
        Возвращает URL текущей сети.

        Returns:
            str: URL WebSocket
        """
        if self.testnet:
            return "wss://stream-testnet.bybit.com/v5/public"
        return "wss://stream.bybit.com/v5/public"

    def get_current_network(self) -> str:
        """
        Возвращает текущую сеть.

        Returns:
            str: "testnet" или "mainnet"
        """
        return "testnet" if self.testnet else "mainnet"

    # ─── Представление ──────────────────────────────────────────────

    @property
    def is_connected_public(self) -> bool:
        """Проверка публичного подключения."""
        return self._connected_public

    @property
    def is_connected_private(self) -> bool:
        """Проверка приватного подключения."""
        return self._connected_private

    def __repr__(self) -> str:
        network = self.get_current_network()
        return (
            f"BybitWebSocketClient(network={network}, "
            f"public={self._connected_public}, "
            f"private={self._connected_private})"
        )

    async def __aenter__(self):
        """Async context manager — вход."""
        await self.connect_public()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager — выход."""
        await self.close()
