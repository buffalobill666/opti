"""
Pydantic модели для OptionsRunner.

Включает:
  - Модели стратегий (Strategy, StrategyCreate, StrategyUpdate, ...)
  - Модели API ключей (APICredentials, APICredentialsPartial, ...)
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ============================================================
#  Модели API ключей (используются в api_keys_routes)
# ============================================================

class APICredentials(BaseModel):
    """Модель API ключей для сохранения."""
    exchange: str
    api_key: str
    api_secret: str
    testnet: bool = False


class APICredentialsPartial(BaseModel):
    """Модель частичного обновления ключей."""
    exchange: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    testnet: bool = False


class NetworkSwitch(BaseModel):
    """Модель переключения сети."""
    exchange: str
    testnet: bool = False


class TestConnectionRequest(BaseModel):
    """Модель тестирования подключения."""
    exchange: str
    api_key: str
    api_secret: str
    testnet: bool = False
    is_demo: bool = False


# ============================================================
#  Модели ордеров (используются в orders_routes)
# ============================================================

class OrderRequest(BaseModel):
    """Модель создания ордера."""
    symbol: str
    side: str
    order_type: str
    qty: str
    price: Optional[str] = None
    order_link_id: Optional[str] = None
    time_in_force: Optional[str] = "GTC"
    # Общие / расширенные параметры
    reduce_only: Optional[bool] = False
    # Bybit (опционы)
    close_on_trigger: Optional[bool] = False
    order_iv: Optional[str] = None
    mmp: Optional[bool] = False
    take_profit: Optional[str] = None
    stop_loss: Optional[str] = None
    tp_limit_price: Optional[str] = None
    sl_limit_price: Optional[str] = None
    tp_trigger_by: Optional[str] = None
    sl_trigger_by: Optional[str] = None
    # Deribit
    post_only: Optional[bool] = True
    label: Optional[str] = None
    advanced: Optional[str] = None
    trigger_price: Optional[str] = None
    trigger_offset: Optional[str] = None
    trigger: Optional[str] = None


class AmendOrderRequest(BaseModel):
    """Модель изменения ордера."""
    symbol: str
    order_id: Optional[str] = None
    order_link_id: Optional[str] = None
    price: Optional[str] = None
    qty: Optional[str] = None


class CancelOrderRequest(BaseModel):
    """Модель отмены ордера."""
    symbol: str
    order_id: Optional[str] = None
    order_link_id: Optional[str] = None


# ============================================================
#  Модели стратегий
# ============================================================


# ─── Enum-ы ─────────────────────────────────────────────────────────

class AssetType(str, Enum):
    """Тип актива."""
    BTC = "BTC"
    ETH = "ETH"
    OTHER = "Other"


class VolumeCurrency(str, Enum):
    """Валюта объёма."""
    ASSET = "asset"
    USDT = "USDT"


class ContractPeriod(str, Enum):
    """Период контракта."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ContractPosition(str, Enum):
    """Позиция контракта."""
    NEAREST = "nearest"
    MIDDLE = "middle"
    FARTHEST = "farthest"


class EntryType(str, Enum):
    """Тип входа."""
    CALL = "Call"
    PUT = "Put"
    CALL_PUT = "Call+Put"


class TriggerType(str, Enum):
    """Тип триггера для SL/TP."""
    CONDITIONS = "conditions"
    WEBHOOK = "webhook"


# ─── Вложенные модели ───────────────────────────────────────────────

class ContractConfig(BaseModel):
    """Конфигурация контракта."""
    period: ContractPeriod
    position: ContractPosition


class WebhookConfig(BaseModel):
    """Конфигурация webhook."""
    enabled: bool = False
    name: str = ""


class ConditionConfig(BaseModel):
    """Конфигурация условий для SL/TP."""
    enabled: bool = False
    price: Optional[float] = None
    percent: Optional[float] = None


class StopLossConfig(BaseModel):
    """Конфигурация StopLoss."""
    trigger_type: TriggerType = TriggerType.CONDITIONS
    conditions: Optional[ConditionConfig] = None
    webhook: Optional[WebhookConfig] = None


class TakeProfitConfig(BaseModel):
    """Конфигурация TakeProfit."""
    trigger_type: TriggerType = TriggerType.CONDITIONS
    conditions: Optional[ConditionConfig] = None
    webhook: Optional[WebhookConfig] = None


# ─── Основная модель стратегии ──────────────────────────────────────

class Strategy(BaseModel):
    """Модель торговой стратегии."""
    id: str = Field(default="", description="Уникальный ID (генерируется при создании)")
    name: str = Field(..., min_length=1, max_length=100, description="Название стратегии")
    description: str = Field(default="", max_length=500, description="Описание")

    # Актив
    asset_type: AssetType = AssetType.BTC
    custom_asset: str = Field(default="", description="Кастомный тикер если asset_type=Other")

    # Объём
    volume: float = Field(default=0.0, gt=0, description="Объём")
    volume_currency: VolumeCurrency = VolumeCurrency.USDT
    volume_split: bool = Field(default=False, description="Разделить объём на контракты")
    split_count: int = Field(default=1, ge=1, description="Количество контрактов для разделения")

    # Контракты
    contracts: list[ContractConfig] = Field(default_factory=list)

    # Тип входа
    entry_type: EntryType = EntryType.CALL

    # Webhook входа
    entry_webhook: WebhookConfig = Field(default_factory=WebhookConfig)

    # StopLoss / TakeProfit
    stop_loss: StopLossConfig = Field(default_factory=StopLossConfig)
    take_profit: TakeProfitConfig = Field(default_factory=TakeProfitConfig)

    # Мета
    created_at: str = Field(default="", description="Время создания")
    updated_at: str = Field(default="", description="Время обновления")
    is_active: bool = Field(default=True, description="Активна ли стратегия")


class StrategyList(BaseModel):
    """Список стратегий (для API ответа)."""
    strategies: list[Strategy]
    total: int


class StrategyCreate(BaseModel):
    """Модель для создания стратегии (без id и timestamps)."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    asset_type: AssetType = AssetType.BTC
    custom_asset: str = ""
    volume: float = 0.0
    volume_currency: VolumeCurrency = VolumeCurrency.USDT
    volume_split: bool = False
    split_count: int = 1
    contracts: list[ContractConfig] = []
    entry_type: EntryType = EntryType.CALL
    entry_webhook: WebhookConfig = {}
    stop_loss: StopLossConfig = {}
    take_profit: TakeProfitConfig = {}
    is_active: bool = True


class StrategyUpdate(BaseModel):
    """Модель для обновления стратегии (все поля опциональны)."""
    name: Optional[str] = None
    description: Optional[str] = None
    asset_type: Optional[AssetType] = None
    custom_asset: Optional[str] = None
    volume: Optional[float] = None
    volume_currency: Optional[VolumeCurrency] = None
    volume_split: Optional[bool] = None
    split_count: Optional[int] = None
    contracts: Optional[list[ContractConfig]] = None
    entry_type: Optional[EntryType] = None
    entry_webhook: Optional[WebhookConfig] = None
    stop_loss: Optional[StopLossConfig] = None
    take_profit: Optional[TakeProfitConfig] = None
    is_active: Optional[bool] = None
