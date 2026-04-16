"""
HTTP клиент для работы с Deribit API v2.

Использует JSON-RPC 2.0 поверх HTTP для всех запросов.
Аутентификация: OAuth 2.0 через public/auth (client_credentials).

URL-адреса:
    Mainnet: https://www.deribit.com/api/v2
    Testnet: https://test.deribit.com/api/v2

Документация:
    API Reference: https://docs.deribit.com/api-reference
    Authentication: https://support.deribit.com/hc/en-us/articles/29748629634205
    JSON-RPC: https://www.jsonrpc.org/specification
"""

import time
import aiohttp
from typing import Optional

from utils.logger import logger, log_api_request, log_api_request_detail
from utils.timer import timed_execution


# ─── Коды ошибок Deribit ────────────────────────────────────────────
ERROR_CODES = {
    13000: "Invalid or expired token",
    13001: "Authorization required",
    13002: "Invalid login",
    13003: "Invalid or expired refresh token",
    13004: "Too many requests",
    13005: "Expired token",
    13006: "Invalid client_id",
    13007: "Invalid client_secret",
    13008: "Invalid grant_type",
    13009: "Invalid scope",
    13010: "Invalid redirect_uri",
    20000: "Rate limit exceeded",
    10000: "Invalid request",
    10001: "Method not found",
    10002: "Invalid params",
    10003: "Internal error",
    10004: "Parse error",
    10005: "Invalid JSON-RPC",
    10006: "Invalid version",
}


class DeribitClient:
    """
    Клиент для работы с Deribit API v2 (JSON-RPC over HTTP).

    Аутентификация: OAuth 2.0 через public/auth.
    Документация: https://support.deribit.com/hc/en-us/articles/29748629634205

    Пример использования:
        client = DeribitClient(
            client_id="your_api_key",
            client_secret="your_api_secret",
            testnet=True
        )
        await client.authenticate()
        result = await client.call_private(
            method="private/get_account_summary",
            params={"currency": "BTC"}
        )
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        testnet: bool = False,
        timeout: int = 30,
    ):
        """
        Инициализация клиента.

        Args:
            client_id: API Key (Client ID)
            client_secret: API Secret (Client Secret)
            testnet: Использовать тестовую сеть (test.deribit.com)
            timeout: Таймаут HTTP запросов в секундах
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.testnet = testnet
        self.timeout = timeout

        # URL-адреса
        self.base_url = (
            "https://test.deribit.com/api/v2"
            if testnet
            else "https://www.deribit.com/api/v2"
        )

        # Токены аутентификации
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: float = 0

        # HTTP сессия
        self._session: Optional[aiohttp.ClientSession] = None

        # Счётчик запросов для rate limiting
        self._request_id = 0

        network = "testnet" if testnet else "mainnet"
        logger.info(
            f"DeribitClient инициализирован | "
            f"network={network} | url={self.base_url}"
        )

    # ─── HTTP сессия ────────────────────────────────────────────────

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получение или создание HTTP сессии."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={"Content-Type": "application/json"},
            )
        return self._session

    async def close(self):
        """Закрытие HTTP сессии."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("HTTP сессия DeribitClient закрыта")

    # ─── Аутентификация ─────────────────────────────────────────────

    @timed_execution
    async def authenticate(self) -> bool:
        """
        Аутентификация через public/auth.

        Grant type: client_credentials
        Scope: trade:read_write, wallet:read_write, account:read_write

        Returns:
            True при успешной аутентификации

        Raises:
            Exception: При ошибке аутентификации
        """
        logger.info(f"Аутентификация Deribit | client_id={self.client_id[:8]}***")

        params = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        start_time = time.perf_counter()

        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/public/auth",
                json={
                    "jsonrpc": "2.0",
                    "id": self._next_id(),
                    "method": "public/auth",
                    "params": params,
                },
            ) as response:
                data = await response.json()
                elapsed = time.perf_counter() - start_time

                if "error" in data:
                    error = data["error"]
                    log_api_request(
                        exchange="deribit",
                        method="public/auth",
                        params={"grant_type": "client_credentials"},
                        elapsed=elapsed,
                        success=False,
                    )
                    raise Exception(
                        f"Ошибка аутентификации: {error.get('message')} "
                        f"(код: {error.get('code')})"
                    )

                result = data.get("result", {})
                self.access_token = result.get("access_token")
                self.refresh_token = result.get("refresh_token")
                expires_in = result.get("expires_in", 0)
                self.token_expires_at = time.time() + expires_in - 60  # 60с запас

                log_api_request(
                    exchange="deribit",
                    method="public/auth",
                    params={"grant_type": "client_credentials"},
                    elapsed=elapsed,
                    success=True,
                )

                logger.info(
                    f"Аутентификация успешна | "
                    f"expires_in={expires_in}s | "
                    f"scope={result.get('scope')}"
                )
                return True

        except aiohttp.ClientError as e:
            elapsed = time.perf_counter() - start_time
            log_api_request(
                exchange="deribit",
                method="public/auth",
                params={"grant_type": "client_credentials"},
                elapsed=elapsed,
                success=False,
            )
            raise Exception(f"Ошибка подключения при аутентификации: {e}")

    @timed_execution
    async def _refresh_token(self) -> bool:
        """
        Обновление access_token через refresh_token.

        Returns:
            True при успешном обновлении

        Raises:
            Exception: При ошибке обновления
        """
        if not self.refresh_token:
            raise Exception("Нет refresh_token для обновления")

        logger.info("Обновление access_token через refresh_token")

        params = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }

        start_time = time.perf_counter()

        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/public/auth",
                json={
                    "jsonrpc": "2.0",
                    "id": self._next_id(),
                    "method": "public/auth",
                    "params": params,
                },
            ) as response:
                data = await response.json()
                elapsed = time.perf_counter() - start_time

                if "error" in data:
                    error = data["error"]
                    log_api_request(
                        exchange="deribit",
                        method="public/auth (refresh)",
                        params={"grant_type": "refresh_token"},
                        elapsed=elapsed,
                        success=False,
                    )
                    # Если refresh_token истёк — полная переаутентификация
                    if error.get("code") == 13003:
                        logger.warning("Refresh token истёк, полная переаутентификация")
                        self.access_token = None
                        self.refresh_token = None
                        return await self.authenticate()

                    raise Exception(
                        f"Ошибка обновления токена: {error.get('message')} "
                        f"(код: {error.get('code')})"
                    )

                result = data.get("result", {})
                self.access_token = result.get("access_token")
                self.refresh_token = result.get("refresh_token")
                expires_in = result.get("expires_in", 0)
                self.token_expires_at = time.time() + expires_in - 60

                log_api_request(
                    exchange="deribit",
                    method="public/auth (refresh)",
                    params={"grant_type": "refresh_token"},
                    elapsed=elapsed,
                    success=True,
                )

                logger.info(f"Access token обновлён | expires_in={expires_in}s")
                return True

        except aiohttp.ClientError as e:
            elapsed = time.perf_counter() - start_time
            # Краткое логирование ошибки
            log_api_request(
                exchange="deribit",
                method="public/auth (refresh)",
                params={"grant_type": "refresh_token"},
                elapsed=elapsed,
                success=False,
            )
            # Детальное логирование ошибки подключения при обновлении токена
            log_api_request_detail(
                exchange="deribit",
                method="public/auth (refresh)",
                url=self.base_url,
                headers={},
                body={"grant_type": "refresh_token"},
                response_status=0,
                response_body={"error": str(e)},
                elapsed=elapsed,
                success=False,
            )
            raise Exception(f"Ошибка подключения при обновлении токена: {e}")

    async def _ensure_authenticated(self):
        """Проверка и обновление токена при необходимости."""
        if not self.access_token:
            await self.authenticate()
            return

        if time.time() >= self.token_expires_at:
            logger.debug("Access token истекает, обновление")
            await self._refresh_token()

    # ─── Основной запрос ────────────────────────────────────────────

    @timed_execution
    async def _request(
        self,
        method: str,
        params: dict = None,
        authenticated: bool = True,
    ) -> dict:
        """
        Выполнение JSON-RPC запроса к Deribit API.

        Args:
            method: Имя метода (напр. "private/buy", "public/get_order_book")
            params: Параметры запроса
            authenticated: Требуется ли аутентификация

        Returns:
            dict: Поле "result" из ответа JSON-RPC

        Raises:
            Exception: При ошибке запроса
        """
        if authenticated:
            await self._ensure_authenticated()

        # Формируем JSON-RPC запрос
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {},
        }

        # Заголовки для приватных методов
        headers = {}
        if authenticated and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token[:8]}****"

        start_time = time.perf_counter()

        try:
            session = await self._get_session()
            async with session.post(
                self.base_url,
                json=payload,
                headers=headers,
            ) as response:
                data = await response.json()
                elapsed = time.perf_counter() - start_time

                success = "error" not in data

                # Детальное логирование
                log_api_request_detail(
                    exchange="deribit",
                    method=method,
                    url=self.base_url,
                    headers=headers,
                    body=payload,
                    response_status=response.status,
                    response_body=data,
                    elapsed=elapsed,
                    success=success,
                )

                # Проверка на ошибки
                if "error" in data:
                    error = data["error"]
                    error_code = error.get("code")
                    error_msg = error.get("message", "Неизвестная ошибка")

                    log_api_request(
                        exchange="deribit",
                        method=method,
                        params=params,
                        elapsed=elapsed,
                        success=False,
                    )

                    # Специфическая обработка кодов ошибок
                    if error_code == 13000:
                        # Invalid or expired token — переаутентификация
                        logger.warning("Токен недействителен, переаутентификация")
                        self.access_token = None
                        self.refresh_token = None
                        await self.authenticate()
                        # Повторный запрос
                        return await self._request(method, params, authenticated)

                    if error_code == 13001:
                        # Authorization required
                        logger.warning("Требуется авторизация, аутентификация")
                        self.access_token = None
                        await self.authenticate()
                        return await self._request(method, params, authenticated)

                    if error_code == 20000:
                        # Rate limit
                        logger.warning(f"Rate limit exceeded | {error_msg}")
                        raise Exception(
                            f"Rate limit exceeded: {error_msg} "
                            f"(код: {error_code})"
                        )

                    # Общая ошибка
                    error_description = ERROR_CODES.get(
                        error_code, error_msg
                    )
                    raise Exception(
                        f"Deribit API ошибка: {error_description} "
                        f"(код: {error_code})"
                    )

                # Успешный ответ
                result = data.get("result")

                log_api_request(
                    exchange="deribit",
                    method=method,
                    params=params,
                    elapsed=elapsed,
                    success=True,
                )

                return result

        except aiohttp.ClientError as e:
            elapsed = time.perf_counter() - start_time
            # Краткое логирование ошибки
            log_api_request(
                exchange="deribit",
                method=method,
                params=params,
                elapsed=elapsed,
                success=False,
            )
            # Детальное логирование ошибки подключения
            log_api_request_detail(
                exchange="deribit",
                method=method,
                url=self.base_url,
                headers=headers,
                body=payload,
                response_status=0,
                response_body={"error": str(e)},
                elapsed=elapsed,
                success=False,
            )
            raise Exception(f"Ошибка подключения к Deribit API: {e}")

    # ─── Публичные и приватные методы ───────────────────────────────

    async def call_public(self, method: str, params: dict = None) -> dict:
        """
        Вызов публичного метода (без аутентификации).

        Args:
            method: Имя метода (напр. "public/get_order_book")
            params: Параметры запроса

        Returns:
            dict: Результат запроса

        Пример:
            result = await client.call_public(
                method="public/get_order_book",
                params={"instrument_name": "BTC-27DEC24-80000-C", "depth": 10}
            )
        """
        # Убедимся что метод публичный
        if not method.startswith("public/"):
            method = f"public/{method}"

        return await self._request(method, params, authenticated=False)

    async def call_private(self, method: str, params: dict = None) -> dict:
        """
        Вызов приватного метода (с аутентификацией).

        Args:
            method: Имя метода (напр. "private/buy")
            params: Параметры запроса

        Returns:
            dict: Результат запроса

        Пример:
            result = await client.call_private(
                method="private/buy",
                params={
                    "instrument_name": "BTC-27DEC24-80000-C",
                    "amount": 1,
                    "type": "limit",
                    "price": 1500
                }
            )
        """
        # Убедимся что метод приватный
        if not method.startswith("private/"):
            method = f"private/{method}"

        return await self._request(method, params, authenticated=True)

    # ─── Переключение сети ──────────────────────────────────────────

    def switch_network(self, testnet: bool):
        """
        Переключение между testnet и mainnet.

        Сбрасывает токены — потребуется новая аутентификация.

        Args:
            testnet: True = test.deribit.com, False = www.deribit.com

        Пример:
            client.switch_network(True)  # Переключить на testnet
        """
        old_network = "mainnet" if not self.testnet else "testnet"
        new_network = "testnet" if testnet else "mainnet"

        self.testnet = testnet
        self.base_url = (
            "https://test.deribit.com/api/v2"
            if testnet
            else "https://www.deribit.com/api/v2"
        )

        # Сбросить токены — потребуется новая аутентификация
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = 0

        logger.info(
            f"Deribit сеть переключена: {old_network} → {new_network} | "
            f"url={self.base_url}"
        )

    def get_network_url(self) -> str:
        """
        Возвращает текущий URL сети.

        Returns:
            str: URL текущей сети
        """
        return self.base_url

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

    def __repr__(self) -> str:
        network = self.get_current_network()
        return (
            f"DeribitClient(network={network}, "
            f"authenticated={self.access_token is not None})"
        )

    async def __aenter__(self):
        """Async context manager — вход."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager — выход."""
        await self.close()
