"""
HTTP клиент для работы с Bybit API v5.

Использует pybit SDK (официальная библиотека Bybit).
Поддерживает торговлю опционами через Unified Trading Account.

URL-адреса:
    Mainnet REST: https://api.bybit.com
    Testnet REST: https://api-testnet.bybit.com

Документация:
    V5 API Overview: https://bybit-exchange.github.io/docs/v5/intro
    pybit SDK: https://github.com/bybit-exchange/pybit
    Options Trading: https://bybit-exchange.github.io/docs/v5/market/instrument
"""

import time
import json
from typing import Optional

from pybit.unified_trading import HTTP
from pybit import _helpers
import requests

from utils.logger import logger, log_api_request, log_api_request_detail
from utils.timer import timed_execution


# ─── Патч таймстампа pybit ──────────────────────────────────────────
# Bybit сервер возвращает Timenow в заголовках каждого ответа.
# Используем его для компенсации рассинхрона часов.

_server_time_offset = 0  # Смещение наших часов относительно сервера (мс)


def _patched_generate_timestamp():
    """
    Генерация таймстампа с компенсацией рассинхрона часов.

    offset = local_time - server_time (положительный = наши часы ВПЕРЕДИ)
    corrected_timestamp = local_time - offset = server_time
    """
    global _server_time_offset

    local_ms = int(time.time() * 1000)
    return local_ms - _server_time_offset


def _update_server_time(timenow_ms: int):
    """Обновить серверное время из заголовка ответа."""
    global _server_time_offset
    local_ms = int(time.time() * 1000)
    _server_time_offset = local_ms - timenow_ms


# Применяем патч во ВСЕХ модулях pybit где используется generate_timestamp
import pybit._helpers as _helpers_mod
import pybit._http_manager as _http_mod

_helpers_mod.generate_timestamp = _patched_generate_timestamp
_http_mod.generate_timestamp = _patched_generate_timestamp


class BybitClient:
    """
    Клиент для работы с Bybit API v5 (Unified Trading).

    Использует pybit SDK для HTTP запросов.
    Поддерживает опционы через category="option".

    Пример использования:
        client = BybitClient(
            api_key="your_api_key",
            api_secret="your_api_secret",
            testnet=True
        )
        result = await client.call_private(
            method="get_wallet_balance",
            params={"accountType": "UNIFIED", "coin": "USDC"}
        )
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = False,
        demo: bool = False,
    ):
        """
        Инициализация клиента.

        Args:
            api_key: API ключ
            api_secret: API секрет
            testnet: Использовать тестовую сеть (api-testnet.bybit.com)
            demo: Использовать Demo Trading (api-demo.bybit.com)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.demo = demo

        # pybit HTTP сессия
        self._session: Optional[HTTP] = None

        # URL-адреса
        if demo:
            self._base_url = "https://api-demo.bybit.com"
        elif testnet:
            self._base_url = "https://api-testnet.bybit.com"
        else:
            self._base_url = "https://api.bybit.com"

        self._initialize_session()

        mode = "demo" if demo else ("testnet" if testnet else "mainnet")
        logger.info(
            f"BybitClient инициализирован | "
            f"mode={mode} | url={self._base_url}"
        )

    def _initialize_session(self):
        """Создание pybit HTTP сессии с перехватом запросов."""
        self._session = HTTP(
            testnet=self.testnet,
            demo=self.demo,
            api_key=self.api_key,
            api_secret=self.api_secret,
            log_requests=True,
            logging_level=10,
            recv_window=10000,
            max_retries=1,
            # 10002 = timestamp error — ретраим, наш патч сгенерирует правильный timestamp
            retry_codes={10002},
        )

        # Monkey-patch requests.Session.send для перехвата полных запросов
        original_send = self._session.client.send

        def patched_send(request, **kwargs):
            """Перехват полного запроса с заголовками и телом."""
            start = time.perf_counter()

            # Логируем ПОЛНЫЙ запрос
            full_url = request.url
            full_headers = dict(request.headers)
            full_body = request.body if request.body else ""

            logger.debug(
                f"BYBIT REQUEST:\n"
                f"  Method: {request.method}\n"
                f"  URL: {full_url}\n"
                f"  Headers: {json.dumps(full_headers, indent=4, ensure_ascii=False)}\n"
                f"  Body: {full_body}"
            )

            # Отправляем запрос
            response = original_send(request, **kwargs)
            elapsed = time.perf_counter() - start

            # Обновляем серверное время из заголовка Timenow
            timenow = response.headers.get("Timenow")
            if timenow:
                _update_server_time(int(timenow))

            # Логируем ПОЛНЫЙ ответ
            logger.debug(
                f"BYBIT RESPONSE:\n"
                f"  Status: {response.status_code}\n"
                f"  Headers: {json.dumps(dict(response.headers), indent=4, ensure_ascii=False)}\n"
                f"  Body: {response.text[:5000]}"
            )

            return response

        self._session.client.send = patched_send

        # Синхронизация времени с сервером Bybit
        self._sync_server_time()

        logger.debug(
            f"pybit HTTP сессия создана | "
            f"api_key={self.api_key} | "
            f"api_secret={self.api_secret} | "
            f"testnet={self.testnet} | "
            f"time_offset={_server_time_offset}ms"
        )

    def _sync_server_time(self):
        """
        Синхронизация локального времени с сервером Bybit.

        Делает публичный запрос и вычисляет разницу часов.
        """
        try:
            # Публичный запрос — не требует подписи
            resp = self._session.client.get(
                f"{self._base_url}/v5/market/time",
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                server_time = data.get("time") or data.get("result", {}).get("timeNano")
                if server_time:
                    # timeNano — наносекунды, делим на 10^6
                    server_ms = int(server_time) // 1_000_000 if int(server_time) > 10**15 else int(server_time)
                    _update_server_time(server_ms)
                    logger.debug(
                        f"Синхронизация времени: offset={_server_time_offset}ms"
                    )
                    return
        except Exception:
            pass

        # Fallback: пробуем получить время из заголовка публичного запроса
        try:
            resp = self._session.client.get(
                f"{self._base_url}/v5/market/instruments-info",
                params={"category": "option", "baseCoin": "BTC", "limit": "1"},
                timeout=5,
            )
            timenow = resp.headers.get("Timenow")
            if timenow:
                _update_server_time(int(timenow))
                logger.debug(
                    f"Синхронизация времени (fallback): offset={_server_time_offset}ms"
                )
        except Exception as e:
            logger.warning(f"Не удалось синхронизировать время: {e}")

    # ─── Переключение сети ──────────────────────────────────────────

    def switch_network(self, testnet: bool = False, demo: bool = False):
        """
        Переключение между режимами.

        Args:
            testnet: True = api-testnet.bybit.com
            demo: True = api-demo.bybit.com
        """
        old_mode = "demo" if self.demo else ("testnet" if self.testnet else "mainnet")
        new_mode = "demo" if demo else ("testnet" if testnet else "mainnet")

        self.testnet = testnet
        self.demo = demo

        if demo:
            self._base_url = "https://api-demo.bybit.com"
        elif testnet:
            self._base_url = "https://api-testnet.bybit.com"
        else:
            self._base_url = "https://api.bybit.com"

        # Пересоздать сессию
        self._initialize_session()

        logger.info(
            f"Bybit режим переключён: {old_mode} → {new_mode} | "
            f"url={self._base_url}"
        )

    def get_network_url(self) -> str:
        """
        Возвращает текущий URL сети.

        Returns:
            str: URL текущей сети
        """
        return self._base_url

    def get_current_network(self) -> str:
        """
        Возвращает текущий режим.

        Returns:
            str: "demo", "testnet" или "mainnet"
        """
        if self.demo:
            return "demo"
        return "testnet" if self.testnet else "mainnet"

    # ─── Публичные запросы ──────────────────────────────────────────

    @timed_execution
    async def call_public(self, method: str, params: dict = None) -> dict:
        """
        Вызов публичного метода (без аутентификации).

        Args:
            method: Имя метода pybit (напр. "get_instruments_info")
            params: Параметры запроса

        Returns:
            dict: Поле "result" из ответа

        Пример:
            result = await client.call_public(
                method="get_instruments_info",
                params={"category": "option", "symbol": "BTC-27DEC24-80000-C"}
            )
        """
        if not self._session:
            self._initialize_session()

        start_time = time.perf_counter()

        try:
            # Маппинг имён методов на pybit методы
            pybit_method = self._resolve_public_method(method)
            result = pybit_method(**(params or {}))

            elapsed = time.perf_counter() - start_time

            # Проверка на ошибки
            ret_code = result.get("retCode", -1)
            success = ret_code == 0

            # Детальное логирование
            log_api_request_detail(
                exchange="bybit",
                method=method,
                url=f"{self._base_url}/v5/market/...",
                headers={"Content-Type": "application/json"},
                body=params or {},
                response_status=200 if success else ret_code,
                response_body=result,
                elapsed=elapsed,
                success=success,
            )

            if not success:
                ret_msg = result.get("retMsg", "Неизвестная ошибка")
                log_api_request(
                    exchange="bybit",
                    method=method,
                    params=params,
                    elapsed=elapsed,
                    success=False,
                )
                raise Exception(
                    f"Bybit API ошибка: {ret_msg} (код: {ret_code})"
                )

            log_api_request(
                exchange="bybit",
                method=method,
                params=params,
                elapsed=elapsed,
                success=True,
            )

            return result.get("result", {})

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            # Краткое логирование ошибки
            log_api_request(
                exchange="bybit",
                method=method,
                params=params,
                elapsed=elapsed,
                success=False,
            )
            # Детальное логирование ошибки
            log_api_request_detail(
                exchange="bybit",
                method=method,
                url=self._base_url,
                headers={"Content-Type": "application/json"},
                body=params or {},
                response_status=0,
                response_body={"error": str(e)},
                elapsed=elapsed,
                success=False,
            )
            raise

    # ─── Приватные запросы ──────────────────────────────────────────

    @timed_execution
    async def call_private(self, method: str, params: dict = None) -> dict:
        """
        Вызов приватного метода (с аутентификацией).

        Args:
            method: Имя метода pybit (напр. "get_wallet_balance")
            params: Параметры запроса

        Returns:
            dict: Поле "result" из ответа

        Пример:
            result = await client.call_private(
                method="get_wallet_balance",
                params={"accountType": "UNIFIED", "coin": "USDC"}
            )
        """
        if not self._session:
            self._initialize_session()

        start_time = time.perf_counter()

        try:
            # Маппинг имён методов на pybit методы
            pybit_method = self._resolve_private_method(method)
            result = pybit_method(**(params or {}))

            elapsed = time.perf_counter() - start_time

            # Проверка на ошибки
            ret_code = result.get("retCode", -1)
            success = ret_code == 0

            # Детальное логирование
            log_api_request_detail(
                exchange="bybit",
                method=method,
                url=f"{self._base_url}/v5/...",
                headers={
                    "Content-Type": "application/json",
                    "X-BAPI-API-KEY": self.api_key,
                },
                body=params or {},
                response_status=200 if success else ret_code,
                response_body=result,
                elapsed=elapsed,
                success=success,
                api_key=self.api_key,
            )

            if not success:
                ret_msg = result.get("retMsg", "Неизвестная ошибка")
                log_api_request(
                    exchange="bybit",
                    method=method,
                    params=params,
                    elapsed=elapsed,
                    success=False,
                )

                # Специфическая обработка кодов ошибок
                if ret_code == 10002:
                    # Invalid parameter — переаутентификация может помочь
                    logger.warning(
                        f"Invalid parameter, пересоздание сессии"
                    )
                    self._initialize_session()

                raise Exception(
                    f"Bybit API ошибка: {ret_msg} (код: {ret_code})"
                )

            log_api_request(
                exchange="bybit",
                method=method,
                params=params,
                elapsed=elapsed,
                success=True,
            )

            return result.get("result", {})

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            # Краткое логирование ошибки
            log_api_request(
                exchange="bybit",
                method=method,
                params=params,
                elapsed=elapsed,
                success=False,
            )
            # Детальное логирование ошибки
            log_api_request_detail(
                exchange="bybit",
                method=method,
                url=self._base_url,
                headers={"Content-Type": "application/json"},
                body=params or {},
                response_status=0,
                response_body={"error": str(e)},
                elapsed=elapsed,
                success=False,
            )
            raise

    # ─── Маппинг методов ────────────────────────────────────────────

    def _resolve_public_method(self, method: str):
        """
        Преобразование имени метода в pybit public метод.

        Поддерживаемые public методы:
            - get_instruments_info      → GET /v5/market/instruments-info
            - get_orderbook             → GET /v5/market/orderbook
            - get_tickers               → GET /v5/market/tickers
            - get_kline                 → GET /v5/market/kline
            - get_public_trade_history  → GET /v5/market/recent-trade
        """
        method_map = {
            "get_instruments_info": self._session.get_instruments_info,
            "get_orderbook": self._session.get_orderbook,
            "get_tickers": self._session.get_tickers,
            "get_kline": self._session.get_kline,
            "get_public_trade_history": self._session.get_public_trade_history,
            "get_funding_rate_history": self._session.get_funding_rate_history,
        }

        if method in method_map:
            return method_map[method]

        # Если метод не найден — пробуем вызвать напрямую
        if hasattr(self._session, method):
            return getattr(self._session, method)

        raise ValueError(
            f"Неизвестный публичный метод: {method}. "
            f"Допустимые: {list(method_map.keys())}"
        )

    def _resolve_private_method(self, method: str):
        """
        Преобразование имени метода в pybit private метод.

        Поддерживаемые private методы:
            - get_wallet_balance        → GET /v5/account/wallet
            - get_positions             → GET /v5/position/list
            - place_order               → POST /v5/order/create
            - amend_order               → POST /v5/order/amend
            - cancel_order              → POST /v5/order/cancel
            - get_open_orders           → GET /v5/order/realtime
            - get_order_history         → GET /v5/order/history
            - set_leverage              → POST /v5/position/set-leverage
            - set_trading_stop          → POST /v5/position/trading-stop
            - get_account_info          → GET /v5/account/fee-rate
            - create_batch_order        → POST /v5/order/create-batch
            - cancel_all_orders         → POST /v5/order/cancel-all
            - get_borrow_history        → GET /v5/account/borrow-history
            - get_collateral_info       → GET /v5/account/collateral-info
            - get_coin_balance          → GET /v5/asset/transfer/query-account-coins-balance
            - create_internal_transfer  → POST /v5/asset/transfer/inter-transfer
            - get_transfer_history      → GET /v5/asset/transfer/query-inter-transfer-list
        """
        method_map = {
            "get_wallet_balance": self._session.get_wallet_balance,
            "get_positions": self._session.get_positions,
            "place_order": self._session.place_order,
            "amend_order": self._session.amend_order,
            "cancel_order": self._session.cancel_order,
            "get_open_orders": self._session.get_open_orders,
            "get_order_history": self._session.get_order_history,
            "set_leverage": self._session.set_leverage,
            "set_trading_stop": self._session.set_trading_stop,
            "get_account_info": self._session.get_account_info,
            "create_batch_order": self._session.place_batch_order,
            "cancel_all_orders": self._session.cancel_all_orders,
            "get_borrow_history": self._session.get_borrow_history,
            "get_collateral_info": self._session.get_collateral_info,
            "get_coin_balance": self._session.get_coin_balance,
            "create_internal_transfer": self._session.create_internal_transfer,
            "set_risk_limit": self._session.set_risk_limit,
            "get_funding_rate_history": self._session.get_funding_rate_history,
        }

        if method in method_map:
            return method_map[method]

        # Если метод не найден — пробуем вызвать напрямую
        if hasattr(self._session, method):
            return getattr(self._session, method)

        raise ValueError(
            f"Неизвестный приватный метод: {method}. "
            f"Допустимые: {list(method_map.keys())}"
        )

    # ─── Представление ──────────────────────────────────────────────

    def __repr__(self) -> str:
        network = self.get_current_network()
        return (
            f"BybitClient(network={network}, "
            f"api_key={self.api_key[:8]}***)"
        )
