"""
Унифицированный клиент для работы с несколькими биржами.

Маршрутизирует запросы на Bybit или Deribit.
Нормализует ответы в единый формат.
Поддерживает переключение testnet/mainnet для каждой биржи.

Использование:
    client = UnifiedClient()

    # Инициализация бирж
    client.init_bybit(api_key="...", api_secret="...", testnet=True)
    client.init_deribit(client_id="...", client_secret="...", testnet=True)

    # Получение балансов
    balances = await client.get_balances("bybit", coin="USDC")
    balances = await client.get_balances("deribit", currency="BTC")

    # Создание ордера
    order = await client.create_order(
        exchange="bybit",
        symbol="BTC-27DEC24-80000-C",
        side="Buy",
        order_type="Limit",
        qty="1",
        price="1500"
    )

    # Переключение сети
    client.switch_network("bybit", testnet=False)  # Переключить на mainnet
    client.switch_network("deribit", testnet=True)  # Переключить на testnet
"""

from typing import Optional

from utils.logger import logger
from utils.timer import timed_execution


# ─── Допустимые биржи ───────────────────────────────────────────────
VALID_EXCHANGES = {"bybit", "deribit"}


class UnifiedClient:
    """
    Унифицированный клиент для работы с Bybit и Deribit.

    Маршрутизирует запросы на нужную биржу.
    Нормализует ответы в единый формат.
    Поддерживает переключение testnet/mainnet.
    """

    def __init__(self):
        """Инициализация унифицированного клиента."""
        # Клиенты бирж
        self.bybit_client = None
        self.deribit_client = None

        # WebSocket клиенты
        self.bybit_ws = None
        self.deribit_ws = None

        # Текущие режимы
        self.bybit_testnet = False
        self.bybit_demo = False
        self.deribit_testnet = False

        logger.info("UnifiedClient инициализирован")

    # ─── Инициализация бирж ─────────────────────────────────────────

    def init_bybit(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = False,
        demo: bool = False,
    ):
        """
        Инициализация Bybit клиента.

        Args:
            api_key: API ключ
            api_secret: API секрет
            testnet: False = mainnet (api.bybit.com), True = testnet (api-testnet.bybit.com)
            demo: True = Demo Trading (api-demo.bybit.com)
        """
        from client.bybit.bybit_client import BybitClient
        from client.bybit.bybit_websocket import BybitWebSocketClient

        self.bybit_client = BybitClient(
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet,
            demo=demo,
        )
        self.bybit_ws = BybitWebSocketClient(
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet,
        )
        self.bybit_testnet = testnet
        self.bybit_demo = demo

        mode = "demo" if demo else ("testnet" if testnet else "mainnet")
        logger.info(
            f"Bybit клиент инициализирован | "
            f"mode={mode}"
        )

    async def init_bybit_async(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = False,
        demo: bool = False,
    ):
        """Инициализация Bybit с подключением WebSocket."""
        self.init_bybit(api_key, api_secret, testnet, demo)
        try:
            await self.bybit_ws.connect_public()
            logger.info("Bybit WebSocket подключён")
        except Exception as e:
            logger.warning(f"Bybit WebSocket не подключился: {e}")

    def init_deribit(
        self,
        client_id: str,
        client_secret: str,
        testnet: bool = False,
    ):
        """
        Инициализация Deribit клиента.

        Args:
            client_id: Client ID
            client_secret: Client Secret
            testnet: False = mainnet (www.deribit.com), True = testnet (test.deribit.com)
        """
        from client.deribit.deribit_client import DeribitClient
        from client.deribit.deribit_websocket import DeribitWebSocketClient

        self.deribit_client = DeribitClient(
            client_id=client_id,
            client_secret=client_secret,
            testnet=testnet,
        )
        self.deribit_ws = DeribitWebSocketClient(
            client_id=client_id,
            client_secret=client_secret,
            testnet=testnet,
        )
        self.deribit_testnet = testnet

        logger.info(
            f"Deribit клиент инициализирован | "
            f"network={'testnet' if testnet else 'mainnet'}"
        )

    async def init_deribit_async(
        self,
        client_id: str,
        client_secret: str,
        testnet: bool = False,
    ):
        """Инициализация Deribit с подключением WebSocket."""
        self.init_deribit(client_id, client_secret, testnet)
        try:
            await self.deribit_ws.connect()
            logger.info("Deribit WebSocket подключён")
        except Exception as e:
            logger.warning(f"Deribit WebSocket не подключился: {e}")

    # ─── Переключение режима ──────────────────────────────────────────

    def switch_network(self, exchange: str, testnet: bool = False, demo: bool = False):
        """
        Переключение режима для указанной биржи.

        Args:
            exchange: "bybit" или "deribit"
            testnet: True = testnet
            demo: True = Demo Trading (только для Bybit)
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            if self.bybit_client:
                self.bybit_client.switch_network(testnet=testnet, demo=demo)
            if self.bybit_ws:
                self.bybit_ws.switch_network(testnet)
            self.bybit_testnet = testnet
            self.bybit_demo = demo
        else:
            if self.deribit_client:
                self.deribit_client.switch_network(testnet)
            if self.deribit_ws:
                self.deribit_ws.switch_network(testnet)
            self.deribit_testnet = testnet

        mode = "demo" if demo else ("testnet" if testnet else "mainnet")
        logger.info(
            f"{exchange.upper()} переключён на {mode}"
        )

    def get_current_network(self, exchange: str) -> str:
        """
        Возвращает текущий режим для биржи.

        Args:
            exchange: "bybit" или "deribit"

        Returns:
            str: "demo", "testnet" или "mainnet"
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            if self.bybit_demo:
                return "demo"
            return "testnet" if self.bybit_testnet else "mainnet"
        return "testnet" if self.deribit_testnet else "mainnet"

    def get_network_url(self, exchange: str) -> str:
        """
        Возвращает URL текущей сети для биржи.

        Args:
            exchange: "bybit" или "deribit"

        Returns:
            str: URL текущей сети
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            if self.bybit_client:
                return self.bybit_client.get_network_url()
            return (
                "https://api-testnet.bybit.com"
                if self.bybit_testnet
                else "https://api.bybit.com"
            )
        else:
            if self.deribit_client:
                return self.deribit_client.get_network_url()
            return (
                "https://test.deribit.com/api/v2"
                if self.deribit_testnet
                else "https://www.deribit.com/api/v2"
            )

    # ─── Балансы ────────────────────────────────────────────────────

    @timed_execution
    async def get_balances(self, exchange: str, **kwargs) -> dict:
        """
        Получение балансов.

        Args:
            exchange: "bybit" или "deribit"
            **kwargs: Параметры для конкретной биржи

        Bybit kwargs:
            account_type (str): "UNIFIED" (по умолчанию)
            coin (str): Фильтр по валюте

        Deribit kwargs:
            currency (str): "BTC" или "ETH"

        Returns:
            dict: Нормализованный баланс
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            return await self._get_balances_bybit(**kwargs)
        return await self._get_balances_deribit(**kwargs)

    async def _get_balances_bybit(self, **kwargs) -> dict:
        """Баланс Bybit."""
        from client.bybit.functions.market_data.balances import get_wallet_balance

        account_type = kwargs.get("account_type", "UNIFIED")
        coin = kwargs.get("coin")

        result = await get_wallet_balance(
            self.bybit_client,
            account_type=account_type,
            coin=coin,
        )

        # Нормализация
        return {
            "exchange": "bybit",
            "account_type": result["account_type"],
            "balances": result["coins"],
        }

    async def _get_balances_deribit(self, **kwargs) -> dict:
        """Баланс Deribit."""
        from client.deribit.functions.market_data.balances import get_account_summary

        currency = kwargs.get("currency", "BTC")

        result = await get_account_summary(self.deribit_client, currency=currency)

        # Нормализация
        return {
            "exchange": "deribit",
            "currency": currency,
            "balances": [result],
        }

    # ─── Позиции ────────────────────────────────────────────────────

    @timed_execution
    async def get_positions(self, exchange: str, **kwargs) -> dict:
        """
        Получение открытых позиций.

        Args:
            exchange: "bybit" или "deribit"
            **kwargs: Параметры для конкретной биржи

        Bybit kwargs:
            symbol (str): Символ инструмента
            base_coin (str): "BTC" или "ETH"

        Deribit kwargs:
            currency (str): "BTC", "ETH" или "ALL"

        Returns:
            dict: Нормализованные позиции
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            return await self._get_positions_bybit(**kwargs)
        return await self._get_positions_deribit(**kwargs)

    async def _get_positions_bybit(self, **kwargs) -> dict:
        """Позиции Bybit."""
        from client.bybit.functions.positions.list import get_positions

        result = await get_positions(
            self.bybit_client,
            symbol=kwargs.get("symbol"),
            base_coin=kwargs.get("base_coin"),
        )

        return {
            "exchange": "bybit",
            "positions": result["positions"],
        }

    async def _get_positions_deribit(self, **kwargs) -> dict:
        """Позиции Deribit."""
        from client.deribit.functions.positions.list import get_positions

        result = await get_positions(
            self.deribit_client,
            currency=kwargs.get("currency", "ALL"),
        )

        return {
            "exchange": "deribit",
            "positions": result,
        }

    # ─── Создание ордера ────────────────────────────────────────────

    @timed_execution
    async def create_order(self, exchange: str, **kwargs) -> dict:
        """
        Создание ордера.

        Args:
            exchange: "bybit" или "deribit"
            **kwargs: Параметры ордера

        Bybit kwargs:
            symbol (str): Символ инструмента
            side (str): "Buy" или "Sell"
            order_type (str): "Limit" или "Market"
            qty (str): Количество
            price (str, optional): Цена
            time_in_force (str): "GTC", "IOC", "FOK", "PostOnly"

        Deribit kwargs:
            instrument_name (str): Символ инструмента
            side (str): "buy" или "sell"
            amount (float): Количество
            type (str): "limit", "market"
            price (float, optional): Цена
            time_in_force (str): "good_til_cancelled", "fill_or_kill", "immediate_or_cancel"

        Returns:
            dict: Нормализованный ордер
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            return await self._create_order_bybit(**kwargs)
        return await self._create_order_deribit(**kwargs)

    async def _create_order_bybit(self, **kwargs) -> dict:
        """Ордер Bybit."""
        from client.bybit.functions.orders.create_order import create_order

        result = await create_order(
            self.bybit_client,
            symbol=kwargs["symbol"],
            side=kwargs["side"],
            order_type=kwargs["order_type"],
            qty=kwargs["qty"],
            price=kwargs.get("price"),
            order_link_id=kwargs.get("order_link_id"),
            time_in_force=kwargs.get("time_in_force", "GTC"),
            reduce_only=kwargs.get("reduce_only", False),
            close_on_trigger=kwargs.get("close_on_trigger", False),
            order_iv=kwargs.get("order_iv"),
            mmp=kwargs.get("mmp", False),
            take_profit=kwargs.get("take_profit"),
            stop_loss=kwargs.get("stop_loss"),
            tp_limit_price=kwargs.get("tp_limit_price"),
            sl_limit_price=kwargs.get("sl_limit_price"),
            tp_trigger_by=kwargs.get("tp_trigger_by"),
            sl_trigger_by=kwargs.get("sl_trigger_by"),
        )

        return {
            "exchange": "bybit",
            "order_id": result["order_id"],
            "order_link_id": result["order_link_id"],
            "symbol": result["symbol"],
            "side": result["side"],
            "order_type": result["order_type"],
            "qty": result["qty"],
            "price": result["price"],
            "status": result["order_status"],
        }

    async def _create_order_deribit(self, **kwargs) -> dict:
        """Ордер Deribit."""
        from client.deribit.functions.orders.create_order import create_order

        result = await create_order(
            self.deribit_client,
            instrument_name=kwargs["instrument_name"],
            side=kwargs["side"],
            amount=kwargs["amount"],
            type=kwargs.get("type", "limit"),
            price=kwargs.get("price"),
            time_in_force=kwargs.get("time_in_force", "good_til_cancelled"),
            reduce_only=kwargs.get("reduce_only", False),
            post_only=kwargs.get("post_only", True),
            label=kwargs.get("label"),
            advanced=kwargs.get("advanced"),
            trigger_price=kwargs.get("trigger_price"),
            trigger_offset=kwargs.get("trigger_offset"),
            trigger=kwargs.get("trigger"),
            mmp=kwargs.get("mmp", False),
        )

        return {
            "exchange": "deribit",
            "order_id": result["order_id"],
            "symbol": result["instrument_name"],
            "side": result["direction"],
            "order_type": result["order_type"],
            "qty": str(result["amount"]),
            "price": str(result["price"]),
            "status": result["order_state"],
        }

    # ─── Изменение ордера ───────────────────────────────────────────

    @timed_execution
    async def amend_order(self, exchange: str, **kwargs) -> dict:
        """
        Изменение ордера.

        Args:
            exchange: "bybit" или "deribit"
            **kwargs: Параметры изменения

        Returns:
            dict: Нормализованные данные ордера
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            return await self._amend_order_bybit(**kwargs)
        return await self._amend_order_deribit(**kwargs)

    async def _amend_order_bybit(self, **kwargs) -> dict:
        """Изменение ордера Bybit."""
        from client.bybit.functions.orders.amend_order import amend_order

        result = await amend_order(
            self.bybit_client,
            symbol=kwargs["symbol"],
            order_id=kwargs.get("order_id"),
            order_link_id=kwargs.get("order_link_id"),
            price=kwargs.get("price"),
            qty=kwargs.get("qty"),
        )

        return {
            "exchange": "bybit",
            "order_id": result["order_id"],
            "symbol": result["symbol"],
            "qty": result["qty"],
            "price": result["price"],
            "status": result["order_status"],
        }

    async def _amend_order_deribit(self, **kwargs) -> dict:
        """Изменение ордера Deribit."""
        from client.deribit.functions.orders.amend_order import amend_order

        result = await amend_order(
            self.deribit_client,
            order_id=kwargs["order_id"],
            amount=kwargs.get("amount"),
            price=kwargs.get("price"),
        )

        return {
            "exchange": "deribit",
            "order_id": result["order_id"],
            "symbol": result["instrument_name"],
            "qty": str(result["amount"]),
            "price": str(result["price"]),
            "status": result["order_state"],
        }

    # ─── Отмена ордера ──────────────────────────────────────────────

    @timed_execution
    async def cancel_all_orders(self, exchange: str, **kwargs) -> dict:
        """
        Отмена всех активных ордеров.

        Args:
            exchange: "bybit" или "deribit"
            **kwargs: Параметры отмены

        Returns:
            dict: Результат отмены
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            return await self._cancel_all_orders_bybit(**kwargs)
        return await self._cancel_all_orders_deribit(**kwargs)

    async def _cancel_all_orders_bybit(self, **kwargs) -> dict:
        """Отмена всех ордеров Bybit."""
        from client.bybit.functions.orders.cancel_all import cancel_all_orders

        result = await cancel_all_orders(
            self.bybit_client,
            base_coin=kwargs.get("base_coin"),
            symbol=kwargs.get("symbol"),
        )

        return {
            "exchange": "bybit",
            "success": result["success"],
            "cancelled_count": result["cancelled_count"],
        }

    async def _cancel_all_orders_deribit(self, **kwargs) -> dict:
        """Отмена всех ордеров Deribit."""
        from client.deribit.functions.orders.cancel_all import cancel_all_orders

        result = await cancel_all_orders(
            self.deribit_client,
            type=kwargs.get("type", "all"),
        )

        return {
            "exchange": "deribit",
            "cancelled_count": result["cancelled_count"],
            "type": result["type"],
        }

    @timed_execution
    async def close_position(self, exchange: str, **kwargs) -> dict:
        """
        Закрытие позиции.

        Args:
            exchange: "bybit" или "deribit"
            **kwargs: Параметры закрытия

        Returns:
            dict: Данные закрывающего ордера
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            return await self._close_position_bybit(**kwargs)
        return await self._close_position_deribit(**kwargs)

    async def _close_position_bybit(self, **kwargs) -> dict:
        """Закрытие позиции Bybit."""
        from client.bybit.functions.positions.close_position import close_position

        result = await close_position(
            self.bybit_client,
            symbol=kwargs["symbol"],
            size=kwargs.get("size"),
        )

        return {
            "exchange": "bybit",
            "order_id": result["order_id"],
            "symbol": result["symbol"],
            "side": result["side"],
            "qty": result["qty"],
            "status": result["status"],
        }

    async def _close_position_deribit(self, **kwargs) -> dict:
        """Закрытие позиции Deribit."""
        from client.deribit.functions.positions.close_position import close_position

        result = await close_position(
            self.deribit_client,
            instrument_name=kwargs["instrument_name"],
            amount=kwargs.get("amount"),
        )

        return {
            "exchange": "deribit",
            "order_id": result["order_id"],
            "symbol": result["instrument_name"],
            "side": result["side"],
            "qty": str(result["amount"]),
            "status": result["order_state"],
        }

    @timed_execution
    async def get_recent_trades(self, exchange: str, **kwargs) -> dict:
        """
        Получение последних сделок.

        Args:
            exchange: "bybit" или "deribit"
            **kwargs: Параметры запроса

        Returns:
            dict: Нормализованные данные сделок
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            return await self._get_recent_trades_bybit(**kwargs)
        return await self._get_recent_trades_deribit(**kwargs)

    async def _get_recent_trades_bybit(self, **kwargs) -> dict:
        """Последние сделки Bybit."""
        from client.bybit.functions.market_data.recent_trades import get_recent_trades

        result = await get_recent_trades(
            self.bybit_client,
            symbol=kwargs["symbol"],
            limit=kwargs.get("limit", 50),
        )

        return {
            "exchange": "bybit",
            "symbol": kwargs["symbol"],
            "trades": result,
        }

    async def _get_recent_trades_deribit(self, **kwargs) -> dict:
        """Последние сделки Deribit."""
        from client.deribit.functions.market_data.recent_trades import get_recent_trades

        result = await get_recent_trades(
            self.deribit_client,
            instrument_name=kwargs["instrument_name"],
            count=kwargs.get("count", 50),
        )

        return {
            "exchange": "deribit",
            "symbol": kwargs["instrument_name"],
            "trades": result["trades"],
            "has_more": result["has_more"],
        }

    # ─── Отмена ордера ──────────────────────────────────────────────

    @timed_execution
    async def cancel_order(self, exchange: str, **kwargs) -> dict:
        """
        Отмена ордера.

        Args:
            exchange: "bybit" или "deribit"
            **kwargs: Параметры отмены

        Returns:
            dict: Нормализованные данные отменённого ордера
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            return await self._cancel_order_bybit(**kwargs)
        return await self._cancel_order_deribit(**kwargs)

    async def _cancel_order_bybit(self, **kwargs) -> dict:
        """Отмена ордера Bybit."""
        from client.bybit.functions.orders.cancel_order import cancel_order

        result = await cancel_order(
            self.bybit_client,
            symbol=kwargs["symbol"],
            order_id=kwargs.get("order_id"),
            order_link_id=kwargs.get("order_link_id"),
        )

        return {
            "exchange": "bybit",
            "order_id": result["order_id"],
            "symbol": result["symbol"],
            "status": "Cancelled",
        }

    async def _cancel_order_deribit(self, **kwargs) -> dict:
        """Отмена ордера Deribit."""
        from client.deribit.functions.orders.cancel_order import cancel_order

        result = await cancel_order(
            self.deribit_client,
            order_id=kwargs["order_id"],
        )

        return {
            "exchange": "deribit",
            "order_id": result["order_id"],
            "symbol": result["instrument_name"],
            "status": "cancelled",
        }

    # ─── История ордеров ────────────────────────────────────────────

    @timed_execution
    async def get_order_history(self, exchange: str, **kwargs) -> dict:
        """
        Получение истории ордеров.

        Args:
            exchange: "bybit" или "deribit"
            **kwargs: Параметры запроса

        Returns:
            dict: Нормализованная история ордеров
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            return await self._get_order_history_bybit(**kwargs)
        return await self._get_order_history_deribit(**kwargs)

    async def _get_order_history_bybit(self, **kwargs) -> dict:
        """История ордеров Bybit."""
        from client.bybit.functions.orders.history import get_order_history

        result = await get_order_history(
            self.bybit_client,
            symbol=kwargs.get("symbol"),
            base_coin=kwargs.get("base_coin"),
            order_status=kwargs.get("order_status"),
            limit=kwargs.get("limit", 20),
        )

        return {
            "exchange": "bybit",
            "orders": result["orders"],
            "next_page_cursor": result.get("next_page_cursor"),
        }

    async def _get_order_history_deribit(self, **kwargs) -> dict:
        """История ордеров Deribit."""
        from client.deribit.functions.orders.history import get_order_history

        result = await get_order_history(
            self.deribit_client,
            currency=kwargs.get("currency", "ALL"),
            count=kwargs.get("count", 10),
            offset=kwargs.get("offset", 0),
        )

        return {
            "exchange": "deribit",
            "orders": result,
        }

    # ─── Рыночные данные ────────────────────────────────────────────

    @timed_execution
    async def get_instruments(self, exchange: str, **kwargs) -> dict:
        """
        Получение списка инструментов.

        Args:
            exchange: "bybit" или "deribit"
            **kwargs: Параметры запроса

        Returns:
            dict: Нормализованный список инструментов
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            return await self._get_instruments_bybit(**kwargs)
        return await self._get_instruments_deribit(**kwargs)

    async def _get_instruments_bybit(self, **kwargs) -> dict:
        """Инструменты Bybit."""
        from client.bybit.functions.market_data.instruments import get_instruments

        result = await get_instruments(
            self.bybit_client,
            base_coin=kwargs.get("base_coin", "BTC"),
            symbol=kwargs.get("symbol"),
            status=kwargs.get("status"),
            limit=kwargs.get("limit", 500),
            classify=kwargs.get("classify", True),
        )

        return {
            "exchange": "bybit",
            "instruments": result["instruments"],
            "next_page_cursor": result.get("next_page_cursor"),
        }

    async def _get_instruments_deribit(self, **kwargs) -> dict:
        """Инструменты Deribit."""
        from client.deribit.functions.market_data.instruments import get_instruments

        result = await get_instruments(
            self.deribit_client,
            currency=kwargs.get("currency", "BTC"),
            classify=kwargs.get("classify", True),
        )

        return {
            "exchange": "deribit",
            "instruments": result,
        }

    @timed_execution
    async def get_orderbook(self, exchange: str, **kwargs) -> dict:
        """
        Получение стакана.

        Args:
            exchange: "bybit" или "deribit"
            **kwargs: Параметры запроса

        Returns:
            dict: Нормализованный стакан
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            return await self._get_orderbook_bybit(**kwargs)
        return await self._get_orderbook_deribit(**kwargs)

    async def _get_orderbook_bybit(self, **kwargs) -> dict:
        """Стакан Bybit."""
        from client.bybit.functions.market_data.orderbook import get_orderbook

        result = await get_orderbook(
            self.bybit_client,
            symbol=kwargs["symbol"],
            limit=kwargs.get("limit", 25),
        )

        return {
            "exchange": "bybit",
            "symbol": result["symbol"],
            "bids": result["bids"],
            "asks": result["asks"],
            "timestamp": result["timestamp"],
        }

    async def _get_orderbook_deribit(self, **kwargs) -> dict:
        """Стакан Deribit."""
        from client.deribit.functions.market_data.orderbook import get_orderbook

        result = await get_orderbook(
            self.deribit_client,
            instrument_name=kwargs["instrument_name"],
            depth=kwargs.get("depth", 10),
        )

        return {
            "exchange": "deribit",
            "symbol": result["instrument_name"],
            "bids": result["bids"],
            "asks": result["asks"],
            "timestamp": result["timestamp"],
            "greeks": result.get("greeks"),
            "mark_iv": result.get("mark_iv"),
        }

    @timed_execution
    async def get_tickers(self, exchange: str, **kwargs) -> dict:
        """
        Получение тикеров.

        Args:
            exchange: "bybit" или "deribit"
            **kwargs: Параметры запроса

        Returns:
            dict: Нормализованные тикеры
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            return await self._get_tickers_bybit(**kwargs)
        return await self._get_tickers_deribit(**kwargs)

    async def _get_tickers_bybit(self, **kwargs) -> dict:
        """Тикеры Bybit."""
        from client.bybit.functions.market_data.tickers import get_tickers

        result = await get_tickers(
            self.bybit_client,
            base_coin=kwargs.get("base_coin"),
            symbol=kwargs.get("symbol"),
        )

        return {
            "exchange": "bybit",
            "tickers": result,
        }

    async def _get_tickers_deribit(self, **kwargs) -> dict:
        """Тикеры Deribit."""
        from client.deribit.functions.market_data.tickers import get_tickers

        result = await get_tickers(
            self.deribit_client,
            currency=kwargs.get("currency", "BTC"),
        )

        return {
            "exchange": "deribit",
            "tickers": result,
        }

    @timed_execution
    async def get_kline(self, exchange: str, **kwargs) -> dict:
        """
        Получение свечей.

        Args:
            exchange: "bybit" или "deribit"
            **kwargs: Параметры запроса

        Returns:
            dict: Нормализованные свечи
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            return await self._get_kline_bybit(**kwargs)
        return await self._get_kline_deribit(**kwargs)

    async def _get_kline_bybit(self, **kwargs) -> dict:
        """Свечи Bybit."""
        from client.bybit.functions.market_data.kline import get_kline

        result = await get_kline(
            self.bybit_client,
            symbol=kwargs["symbol"],
            interval=kwargs.get("interval", "60"),
            start_time=kwargs.get("start_time"),
            end_time=kwargs.get("end_time"),
            limit=kwargs.get("limit", 200),
        )

        return {
            "exchange": "bybit",
            "symbol": kwargs["symbol"],
            "klines": result,
        }

    async def _get_kline_deribit(self, **kwargs) -> dict:
        """Свечи Deribit."""
        from client.deribit.functions.market_data.kline import get_kline

        result = await get_kline(
            self.deribit_client,
            instrument_name=kwargs["instrument_name"],
            start_timestamp=kwargs["start_timestamp"],
            end_timestamp=kwargs["end_timestamp"],
            resolution=kwargs.get("resolution", "60"),
        )

        return {
            "exchange": "deribit",
            "symbol": kwargs["instrument_name"],
            "klines": result,
        }

    # ─── Внутренние переводы ────────────────────────────────────────

    @timed_execution
    async def internal_transfer(self, exchange: str, **kwargs) -> dict:
        """
        Внутренний перевод.

        Args:
            exchange: "bybit" или "deribit"
            **kwargs: Параметры перевода

        Returns:
            dict: Нормализованные данные перевода
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            return await self._internal_transfer_bybit(**kwargs)
        return await self._internal_transfer_deribit(**kwargs)

    async def _internal_transfer_bybit(self, **kwargs) -> dict:
        """Перевод Bybit."""
        from client.bybit.internal_transfers import transfer

        result = await transfer(
            self.bybit_client,
            coin=kwargs["coin"],
            amount=kwargs["amount"],
            from_account_type=kwargs["from_account_type"],
            to_account_type=kwargs["to_account_type"],
            transfer_id=kwargs.get("transfer_id"),
        )

        return {
            "exchange": "bybit",
            "transfer_id": result["transferId"],
            "status": result["status"],
        }

    async def _internal_transfer_deribit(self, **kwargs) -> dict:
        """Перевод Deribit."""
        from client.deribit.internal_transfers import transfer

        result = await transfer(
            self.deribit_client,
            currency=kwargs["currency"],
            amount=kwargs["amount"],
            destination=kwargs["destination"],
            source=kwargs["source"],
        )

        return {
            "exchange": "deribit",
            "transfer_id": result["id"],
            "status": result["state"],
        }

    # ─── TP/SL ──────────────────────────────────────────────────────

    @timed_execution
    async def set_take_stop(self, exchange: str, **kwargs) -> dict:
        """
        Установка TP/SL.

        Args:
            exchange: "bybit" или "deribit"
            **kwargs: Параметры TP/SL

        Returns:
            dict: Нормализованные данные TP/SL
        """
        self._validate_exchange(exchange)

        if exchange == "bybit":
            return await self._set_take_stop_bybit(**kwargs)
        return await self._set_take_stop_deribit(**kwargs)

    async def _set_take_stop_bybit(self, **kwargs) -> dict:
        """TP/SL Bybit."""
        from client.bybit.functions.positions.take_stop import take_stop

        result = await take_stop(
            self.bybit_client,
            symbol=kwargs["symbol"],
            take_profit=kwargs.get("take_profit"),
            stop_loss=kwargs.get("stop_loss"),
            trailing_stop=kwargs.get("trailing_stop"),
            tp_trigger_by=kwargs.get("tp_trigger_by"),
            sl_trigger_by=kwargs.get("sl_trigger_by"),
        )

        return {
            "exchange": "bybit",
            "symbol": result["symbol"],
            "take_profit": result["take_profit"],
            "stop_loss": result["stop_loss"],
        }

    async def _set_take_stop_deribit(self, **kwargs) -> dict:
        """TP/SL Deribit."""
        from client.deribit.functions.positions.take_stop import take_stop

        result = await take_stop(
            self.deribit_client,
            instrument_name=kwargs["instrument_name"],
            side=kwargs["side"],
            amount=kwargs["amount"],
            stop_price=kwargs.get("stop_price"),
            take_profit_price=kwargs.get("take_profit_price"),
        )

        return {
            "exchange": "deribit",
            "symbol": result["instrument_name"],
            "stop_order_id": result["stop_order_id"],
            "tp_order_id": result["tp_order_id"],
        }

    # ─── Валидация ──────────────────────────────────────────────────

    def _validate_exchange(self, exchange: str):
        """
        Проверка валидности биржи.

        Args:
            exchange: "bybit" или "deribit"

        Raises:
            ValueError: Если биржа невалидна
        """
        if exchange not in VALID_EXCHANGES:
            raise ValueError(
                f"Неподдерживаемая биржа: {exchange}. "
                f"Допустимые: {VALID_EXCHANGES}"
            )

        # Проверка инициализации
        if exchange == "bybit" and not self.bybit_client:
            raise Exception(
                "Bybit клиент не инициализирован. "
                "Вызовите init_bybit() перед использованием."
            )
        if exchange == "deribit" and not self.deribit_client:
            raise Exception(
                "Deribit клиент не инициализирован. "
                "Вызовите init_deribit() перед использованием."
            )

    # ─── Представление ──────────────────────────────────────────────

    def __repr__(self) -> str:
        bybit_status = (
            f"bybit={'testnet' if self.bybit_testnet else 'mainnet'}"
            if self.bybit_client
            else "bybit=not_init"
        )
        deribit_status = (
            f"deribit={'testnet' if self.deribit_testnet else 'mainnet'}"
            if self.deribit_client
            else "deribit=not_init"
        )
        return f"UnifiedClient({bybit_status}, {deribit_status})"
