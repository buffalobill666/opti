"""
Pydantic модели для webhook запросов TradingView.

TradingView отправляет JSON-payload при срабатывании алерта.
Этот модуль определяет структуру ожидаемых данных.
"""

from pydantic import BaseModel, Field
from typing import Optional


class TradingViewAlert(BaseModel):
    """
    Стандартный формат алерта TradingView.

    Пример payload от TradingView:
    {
        "exchange": "bybit",
        "symbol": "BTC-27DEC24-80000-C",
        "action": "buy",
        "order_type": "limit",
        "price": 1500,
        "amount": 1,
        "strategy": "My Options Strategy",
        "timestamp": "2024-12-01T10:00:00Z"
    }
    """
    exchange: str = Field(
        ...,
        description="Биржа: 'bybit' или 'deribit'"
    )
    symbol: str = Field(
        ...,
        description="Символ инструмента, напр. 'BTC-27DEC24-80000-C'"
    )
    action: str = Field(
        ...,
        description="Действие: 'buy', 'sell', 'cancel', 'amend', 'close'"
    )
    order_type: Optional[str] = Field(
        None,
        description="Тип ордера: 'limit', 'market'"
    )
    price: Optional[float] = Field(
        None,
        description="Цена ордера"
    )
    amount: Optional[float] = Field(
        None,
        description="Количество контрактов"
    )
    strategy: Optional[str] = Field(
        None,
        description="Имя стратегии"
    )
    timestamp: Optional[str] = Field(
        None,
        description="Временная метка алерта"
    )
    time_in_force: Optional[str] = Field(
        "GTC",
        description="Время действия: GTC, IOC, FOK"
    )
    stop_loss: Optional[float] = Field(
        None,
        description="Цена стоп-лосса"
    )
    take_profit: Optional[float] = Field(
        None,
        description="Цена тейк-профита"
    )
    extra: Optional[dict] = Field(
        None,
        description="Дополнительные параметры"
    )


class WebhookResponse(BaseModel):
    """Ответ webhook сервера."""
    status: str = Field(..., description="ok или error")
    message: str = Field(..., description="Описание результата")
    order_id: Optional[str] = Field(None, description="ID созданного/изменённого ордера")
    exchange: Optional[str] = Field(None, description="Биржа")
    action: Optional[str] = Field(None, description="Выполненное действие")
