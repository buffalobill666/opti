"""
WebSocket клиент для получения данных Deribit в реальном времени.

Использует JSON-RPC 2.0 поверх WebSocket для подписки на потоки данных.

URL-адреса:
    Mainnet WS: wss://www.deribit.com/ws/api/v2
    Testnet WS: wss://test.deribit.com/ws/api/v2

Документация:
    API Reference: https://docs.deribit.com/
    Subscription: https://docs.deribit.com/api-reference/subscription-management
    Authentication: https://support.deribit.com/hc/en-us/articles/29748629634205

Публичные каналы:
    - book.{instrument_name}.{depth}     — стакан заявок
    - ticker.{instrument_name}           — тикеры
    - trade.{instrument_name}            — сделки
    - markprice.options.{base_coin}      — mark price

Приватные каналы:
    - user.orders.{base_coin}            — обновления ордеров
    - user.portfolio.{base_coin}         — портфель
    - user.trades.{base_coin}            — сделки пользователя
"""

import asyncio
import json
import time
from typing import Optional, Callable

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from utils.logger import logger, log_api_request
from utils.timer import timed_execution


class DeribitWebSocketClient:
    """
    WebSocket клиент для получения данных Deribit в реальном времени.

    Поддерживает:
      - Аутентификацию через WebSocket
      - Подписку на публичные и приватные каналы
      - Автоматическое переподключение с exponential backoff
      - Callback-функции для обработки сообщений

    Пример использования:
        ws = DeribitWebSocketClient(
            client_id="your_api_key",
            client_secret="your_api_secret",
            testnet=True
        )

        def handle_orderbook(data):
            print(f"Orderbook update: {data}")

        await ws.connect()
        await ws.subscribe(
            channel="book.BTC-27DEC24-80000-C.10",
            callback=handle_orderbook
        )

        # Бесконечный цикл получения данных
        while True:
            await asyncio.sleep(1)
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        testnet: bool = False,
        reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 60.0,
        reconnect_delay_multiplier: float = 2.0,
    ):
        """
        Инициализация WebSocket клиента.

        Args:
            client_id: API Key (Client ID)
            client_secret: API Secret (Client Secret)
            testnet: Использовать тестовую сеть
            reconnect_delay: Начальная задержка переподключения (сек)
            max_reconnect_delay: Максимальная задержка переподключения (сек)
            reconnect_delay_multiplier: Множитель экспоненциальной задержки
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.testnet = testnet

        # URL WebSocket
        self.ws_url = (
            "wss://test.deribit.com/ws/api/v2"
            if testnet
            else "wss://www.deribit.com/ws/api/v2"
        )

        # Параметры переподключения
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_delay = max_reconnect_delay
        self.reconnect_delay_multiplier = reconnect_delay_multiplier

        # Состояние
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._authenticated = False
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: float = 0

        # Callback-и: {channel: callback_function}
        self.callbacks: dict[str, Callable] = {}

        # Подписки: {channel: callback} — для восстановления при переподключении
        self._subscriptions: dict[str, Callable] = {}

        # Счётчик запросов
        self._request_id = 0
        self._pending_requests: dict[int, asyncio.Future] = {}

        # Задача чтения
        self._read_task: Optional[asyncio.Task] = None

        # Флаг остановки
        self._stop_event = asyncio.Event()

        network = "testnet" if testnet else "mainnet"
        logger.info(
            f"DeribitWebSocketClient инициализирован | "
            f"network={network} | url={self.ws_url}"
        )

    # ─── Подключение ────────────────────────────────────────────────

    @timed_execution
    async def connect(self) -> bool:
        """
        Установка WebSocket соединения.

        Returns:
            True при успешном подключении

        Raises:
            Exception: При ошибке подключения
        """
        if self._connected and self._ws and not self._ws.closed:
            logger.debug("WebSocket уже подключён")
            return True

        logger.info(f"Подключение к WebSocket: {self.ws_url}")

        start_time = time.perf_counter()

        try:
            self._ws = await websockets.connect(
                self.ws_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10,
            )
            self._connected = True
            elapsed = time.perf_counter() - start_time

            logger.info(
                f"WebSocket подключён | {elapsed:.3f}s"
            )

            # Запуск задачи чтения
            self._read_task = asyncio.create_task(self._read_loop())

            return True

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            logger.error(f"Ошибка подключения к WebSocket: {e} | {elapsed:.3f}s")
            self._connected = False
            raise

    async def close(self):
        """Закрытие WebSocket соединения."""
        self._stop_event.set()

        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        if self._ws and not self._ws.closed:
            await self._ws.close()
            self._connected = False
            logger.info("WebSocket соединение закрыто")

    # ─── Аутентификация ─────────────────────────────────────────────

    @timed_execution
    async def authenticate(self) -> bool:
        """
        Аутентификация через WebSocket.

        Метод: public/auth с client_credentials.

        Returns:
            True при успешной аутентификации

        Raises:
            Exception: При ошибке аутентификации
        """
        if not self._connected:
            await self.connect()

        logger.info(f"Аутентификация WebSocket | client_id={self.client_id[:8]}***")

        params = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        start_time = time.perf_counter()

        try:
            result = await self._send_and_wait(
                method="public/auth",
                params=params,
            )
            elapsed = time.perf_counter() - start_time

            self.access_token = result.get("access_token")
            self.refresh_token = result.get("refresh_token")
            expires_in = result.get("expires_in", 0)
            self.token_expires_at = time.time() + expires_in - 60
            self._authenticated = True

            log_api_request(
                exchange="deribit",
                method="public/auth (ws)",
                params={"grant_type": "client_credentials"},
                elapsed=elapsed,
                success=True,
            )

            logger.info(
                f"WebSocket аутентификация успешна | "
                f"expires_in={expires_in}s | "
                f"scope={result.get('scope')}"
            )
            return True

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            log_api_request(
                exchange="deribit",
                method="public/auth (ws)",
                params={"grant_type": "client_credentials"},
                elapsed=elapsed,
                success=False,
            )
            self._authenticated = False
            raise

    async def _ensure_authenticated(self):
        """Проверка и обновление токена при необходимости."""
        if not self._authenticated or not self.access_token:
            await self.authenticate()
            return

        if time.time() >= self.token_expires_at:
            logger.debug("WebSocket access token истекает, обновление")
            await self._refresh_token()

    async def _refresh_token(self) -> bool:
        """Обновление access_token через refresh_token."""
        if not self.refresh_token:
            logger.warning("Нет refresh_token, полная переаутентификация")
            self._authenticated = False
            return await self.authenticate()

        logger.info("Обновление WebSocket access_token")

        params = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }

        try:
            result = await self._send_and_wait(
                method="public/auth",
                params=params,
            )

            self.access_token = result.get("access_token")
            self.refresh_token = result.get("refresh_token")
            expires_in = result.get("expires_in", 0)
            self.token_expires_at = time.time() + expires_in - 60

            logger.info(f"WebSocket access token обновлён | expires_in={expires_in}s")
            return True

        except Exception as e:
            logger.warning(f"Ошибка обновления токена: {e}, переаутентификация")
            self.access_token = None
            self.refresh_token = None
            return await self.authenticate()

    # ─── Подписка на канал ──────────────────────────────────────────

    @timed_execution
    async def subscribe(self, channel: str, callback: Callable) -> bool:
        """
        Подписка на канал данных.

        Публичные каналы:
            - book.{instrument_name}.{depth}  — стакан
              Пример: book.BTC-27DEC24-80000-C.10
            - ticker.{instrument_name}        — тикеры
              Пример: ticker.BTC-27DEC24-80000-C
            - trade.{instrument_name}         — сделки
              Пример: trade.BTC-27DEC24-80000-C
            - markprice.options.{base_coin}   — mark price
              Пример: markprice.options.BTC

        Приватные каналы (требуют аутентификации):
            - user.orders.{base_coin}         — обновления ордеров
              Пример: user.orders.BTC
            - user.portfolio.{base_coin}      — портфель
              Пример: user.portfolio.BTC
            - user.trades.{base_coin}         — сделки пользователя
              Пример: user.trades.BTC

        Args:
            channel: Имя канала
            callback: Функция для обработки данных

        Returns:
            True при успешной подписке

        Raises:
            Exception: При ошибке подписки
        """
        if not self._connected:
            await self.connect()

        # Для приватных каналов — аутентификация
        is_private = channel.startswith("user.")
        if is_private:
            await self._ensure_authenticated()

        logger.info(
            f"Подписка на канал: {channel} | "
            f"{'приватный' if is_private else 'публичный'}"
        )

        params = {"channels": [channel]}

        # Для приватных каналов добавляем access_token
        if is_private and self.access_token:
            params["access_token"] = self.access_token

        try:
            await self._send_and_wait(
                method="public/subscribe" if not is_private else "private/subscribe",
                params=params,
            )

            # Сохраняем callback
            self.callbacks[channel] = callback
            self._subscriptions[channel] = callback

            logger.info(f"Подписка успешна: {channel}")
            return True

        except Exception as e:
            logger.error(f"Ошибка подписки на {channel}: {e}")
            raise

    async def unsubscribe(self, channel: str) -> bool:
        """
        Отписка от канала.

        Args:
            channel: Имя канала

        Returns:
            True при успешной отписке
        """
        if not self._connected:
            logger.warning("Не подключён к WebSocket")
            return False

        logger.info(f"Отписка от канала: {channel}")

        try:
            await self._send_and_wait(
                method="public/unsubscribe",
                params={"channels": [channel]},
            )

            # Удаляем callback
            self.callbacks.pop(channel, None)
            self._subscriptions.pop(channel, None)

            logger.info(f"Отписка успешна: {channel}")
            return True

        except Exception as e:
            logger.error(f"Ошибка отписки от {channel}: {e}")
            raise

    # ─── Отправка запроса с ожиданием ответа ────────────────────────

    async def _send_and_wait(self, method: str, params: dict = None) -> dict:
        """
        Отправка JSON-RPC запроса и ожидание ответа.

        Args:
            method: Имя метода
            params: Параметры запроса

        Returns:
            dict: Поле "result" из ответа
        """
        if not self._connected or not self._ws or self._ws.closed:
            raise Exception("WebSocket не подключён")

        request_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }

        # Создаём Future для ожидания ответа
        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        try:
            await self._ws.send(json.dumps(payload))
            logger.debug(f"Отправлен запрос: {method} (id={request_id})")

            # Ждём ответ с таймаутом
            result = await asyncio.wait_for(future, timeout=30.0)
            return result

        except asyncio.TimeoutError:
            raise Exception(f"Таймаут ответа от сервера: {method}")
        finally:
            self._pending_requests.pop(request_id, None)

    async def _send(self, method: str, params: dict = None) -> int:
        """
        Отправка JSON-RPC запроса без ожидания ответа (fire-and-forget).

        Args:
            method: Имя метода
            params: Параметры запроса

        Returns:
            int: ID запроса
        """
        if not self._connected or not self._ws or self._ws.closed:
            raise Exception("WebSocket не подключён")

        request_id = self._next_id()
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }

        await self._ws.send(json.dumps(payload))
        logger.debug(f"Отправлен запрос (fire-and-forget): {method} (id={request_id})")
        return request_id

    # ─── Цикл чтения ────────────────────────────────────────────────

    async def _read_loop(self):
        """
        Основной цикл чтения сообщений из WebSocket.

        Распределяет входящие сообщения:
          - Ответы на запросы (с "id") → Future в _pending_requests
          - Уведомления (без "id") → callback по каналу
        """
        logger.info("Запуск цикла чтения WebSocket")

        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.warning(f"Невалидный JSON: {message[:100]}")
                except Exception as e:
                    logger.error(f"Ошибка обработки сообщения: {e}")

        except ConnectionClosed as e:
            logger.warning(
                f"WebSocket соединение закрыто | code={e.code} | reason={e.reason}"
            )
            self._connected = False
            self._authenticated = False

            if not self._stop_event.is_set():
                # Автоматическое переподключение
                await self._reconnect()

        except WebSocketException as e:
            logger.error(f"WebSocket ошибка: {e}")
            self._connected = False
            self._authenticated = False

            if not self._stop_event.is_set():
                await self._reconnect()

        except asyncio.CancelledError:
            logger.debug("Цикл чтения отменён")
            raise

        except Exception as e:
            logger.error(f"Неожиданная ошибка в цикле чтения: {e}")
            self._connected = False

            if not self._stop_event.is_set():
                await self._reconnect()

    async def _handle_message(self, data: dict):
        """
        Обработка входящего сообщения.

        Args:
            data: Распарсенный JSON
        """
        # ─── Ответ на запрос (есть "id") ────────────────────────────
        if "id" in data:
            request_id = data["id"]
            future = self._pending_requests.get(request_id)

            if future and not future.done():
                if "error" in data:
                    error = data["error"]
                    future.set_exception(
                        Exception(
                            f"Ошибка сервера: {error.get('message')} "
                            f"(код: {error.get('code')})"
                        )
                    )
                else:
                    future.set_result(data.get("result", {}))
            return

        # ─── Уведомление (нет "id") ─────────────────────────────────
        if "params" in data and "channel" in data["params"]:
            channel = data["params"]["channel"]
            payload = data["params"].get("data", {})

            # Вызываем callback
            callback = self.callbacks.get(channel)
            if callback:
                try:
                    # Проверяем, async callback или нет
                    if asyncio.iscoroutinefunction(callback):
                        await callback(payload)
                    else:
                        callback(payload)
                except Exception as e:
                    logger.error(f"Ошибка в callback для {channel}: {e}")
            else:
                logger.debug(
                    f"Получено уведомление без callback: {channel} | {payload}"
                )
            return

        # ─── Неизвестный формат ──────────────────────────────────────
        logger.debug(f"Неизвестный формат сообщения: {data}")

    # ─── Переподключение ────────────────────────────────────────────

    async def _reconnect(self):
        """
        Автоматическое переподключение с exponential backoff.

        После восстановления соединения:
          - Повторная аутентификация
          - Повторная подписка на все каналы
        """
        delay = self.reconnect_delay
        attempt = 0

        while not self._stop_event.is_set():
            attempt += 1
            logger.info(
                f"Переподключение WebSocket | "
                f"попытка #{attempt} | задержка={delay:.1f}s"
            )

            await asyncio.sleep(delay)

            try:
                # Повторное подключение
                await self.connect()

                # Повторная аутентификация
                if self._authenticated:
                    await self.authenticate()

                # Повторная подписка на все каналы
                for channel, callback in list(self._subscriptions.items()):
                    try:
                        await self.subscribe(channel, callback)
                        logger.info(f"Подписка восстановлена: {channel}")
                    except Exception as e:
                        logger.error(
                            f"Ошибка восстановления подписки {channel}: {e}"
                        )

                logger.info("Переподключение успешно")
                return  # Успех

            except Exception as e:
                logger.warning(
                    f"Переподключение не удалось (попытка #{attempt}): {e}"
                )
                # Экспоненциальная задержка
                delay = min(
                    delay * self.reconnect_delay_multiplier,
                    self.max_reconnect_delay,
                )

    # ─── Переключение сети ──────────────────────────────────────────

    def switch_network(self, testnet: bool):
        """
        Переключение между testnet и mainnet.

        Требует переподключения WebSocket.

        Args:
            testnet: True = wss://test.deribit.com/ws/api/v2
        """
        old_network = "mainnet" if not self.testnet else "testnet"
        new_network = "testnet" if testnet else "mainnet"

        self.testnet = testnet
        self.ws_url = (
            "wss://test.deribit.com/ws/api/v2"
            if testnet
            else "wss://www.deribit.com/ws/api/v2"
        )
        self.access_token = None
        self.refresh_token = None
        self._authenticated = False

        logger.info(
            f"Deribit WebSocket сеть переключена: "
            f"{old_network} → {new_network} | url={self.ws_url}"
        )

        # Если соединение активно — закрыть (переподключится автоматически)
        if self._connected:
            logger.info("Активное соединение будет переподключено к новой сети")
            # Закрываем — _read_loop вызовет _reconnect
            asyncio.create_task(self.close())

    def get_network_url(self) -> str:
        """
        Возвращает текущий URL WebSocket.

        Returns:
            str: URL текущей сети
        """
        return self.ws_url

    def get_current_network(self) -> str:
        """
        Возвращает текущую сеть.

        Returns:
            str: "testnet" или "mainnet"
        """
        return "testnet" if self.testnet else "mainnet"

    # ─── Внутренние утилиты ─────────────────────────────────────────

    def _next_id(self) -> int:
        """Генерация уникального ID для JSON-RPC запроса."""
        self._request_id += 1
        return self._request_id

    @property
    def is_connected(self) -> bool:
        """Проверка подключения."""
        return self._connected and self._ws and not self._ws.closed

    @property
    def is_authenticated(self) -> bool:
        """Проверка аутентификации."""
        return self._authenticated

    def __repr__(self) -> str:
        network = self.get_current_network()
        return (
            f"DeribitWebSocketClient(network={network}, "
            f"connected={self._connected}, "
            f"authenticated={self._authenticated})"
        )

    async def __aenter__(self):
        """Async context manager — вход."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager — выход."""
        await self.close()
