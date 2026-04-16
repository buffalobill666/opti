"""
Утилиты классификации опционных контрактов.

Поддерживает 9 типов контрактов:
- Daily (1 день)
- Bi-Daily (2 дня)
- Tri-Daily (3 дня)
- Weekly (4-7 дней)
- Bi-Weekly (8-14 дней)
- Tri-Weekly (15-21 дней)
- Monthly (22-31 дней)
- Bi-Monthly (32-62 дней)
- Quarterly (> 62 дней)

Использует original_duration_days для Bybit и settlement_period + duration для Deribit.
"""

from datetime import datetime, timezone
from typing import Optional


# ─── Константы классификации ─────────────────────────────────────────

class OptionPeriodType:
    """Типы опционных контрактов."""
    DAILY = "Daily"
    BI_DAILY = "Bi-Daily"
    TRI_DAILY = "Tri-Daily"
    WEEKLY = "Weekly"
    BI_WEEKLY = "Bi-Weekly"
    TRI_WEEKLY = "Tri-Weekly"
    MONTHLY = "Monthly"
    BI_MONTHLY = "Bi-Monthly"
    QUARTERLY = "Quarterly"


# Группы периодов для агрегации
PERIOD_GROUPS = {
    OptionPeriodType.DAILY: "daily",
    OptionPeriodType.BI_DAILY: "daily",
    OptionPeriodType.TRI_DAILY: "daily",
    OptionPeriodType.WEEKLY: "weekly",
    OptionPeriodType.BI_WEEKLY: "weekly",
    OptionPeriodType.TRI_WEEKLY: "weekly",
    OptionPeriodType.MONTHLY: "monthly",
    OptionPeriodType.BI_MONTHLY: "monthly",
    OptionPeriodType.QUARTERLY: "monthly",
}

# Порядок внутри групп
PERIOD_ORDER_IN_GROUP = {
    "daily": [OptionPeriodType.DAILY, OptionPeriodType.BI_DAILY, OptionPeriodType.TRI_DAILY],
    "weekly": [OptionPeriodType.WEEKLY, OptionPeriodType.BI_WEEKLY, OptionPeriodType.TRI_WEEKLY],
    "monthly": [OptionPeriodType.MONTHLY, OptionPeriodType.BI_MONTHLY, OptionPeriodType.QUARTERLY],
}


def classify_by_original_duration(original_duration_days: int) -> str:
    """
    Классифицировать тип опциона по оригинальной длительности контракта.
    
    Args:
        original_duration_days: Количество дней между launchTime и deliveryTime
    
    Returns:
        Тип периода из OptionPeriodType
    """
    if original_duration_days <= 1:
        return OptionPeriodType.DAILY
    elif original_duration_days == 2:
        return OptionPeriodType.BI_DAILY
    elif original_duration_days == 3:
        return OptionPeriodType.TRI_DAILY
    elif 4 <= original_duration_days <= 7:
        return OptionPeriodType.WEEKLY
    elif 8 <= original_duration_days <= 14:
        return OptionPeriodType.BI_WEEKLY
    elif 15 <= original_duration_days <= 21:
        return OptionPeriodType.TRI_WEEKLY
    elif 22 <= original_duration_days <= 31:
        return OptionPeriodType.MONTHLY
    elif 32 <= original_duration_days <= 62:
        return OptionPeriodType.BI_MONTHLY
    else:
        return OptionPeriodType.QUARTERLY


def classify_bybit_option(contract: dict, reference_time_ms: Optional[int] = None) -> dict:
    """
    Классифицировать опцион Bybit на основе launchTime и deliveryTime.
    
    Args:
        contract: dict из API /v5/market/instruments-info
        reference_time_ms: опционально, время для расчёта days_to_expiry
    
    Returns:
        dict с полной информацией о контракте включая классификацию
    """
    # Парсинг timestamp'ов
    launch_ms = int(contract.get("launchTime", 0))
    delivery_ms = int(contract.get("deliveryTime", 0))
    
    # Оригинальная длительность контракта (в днях)
    if launch_ms and delivery_ms:
        original_duration_sec = (delivery_ms - launch_ms) / 1000
        original_duration_days = round(original_duration_sec / (60 * 60 * 24))
    else:
        original_duration_days = 0
    
    # Текущие дни до экспирации (для фильтрации "живых" контрактов)
    now_ms = reference_time_ms or int(datetime.now(timezone.utc).timestamp() * 1000)
    if delivery_ms:
        days_to_expiry = max(0, round((delivery_ms - now_ms) / (1000 * 60 * 60 * 24)))
    else:
        days_to_expiry = None
    
    # Классификация по оригинальной длительности
    period_type = classify_by_original_duration(original_duration_days)
    period_group = PERIOD_GROUPS.get(period_type, "unknown")
    
    # Парсинг страйка из символа: BTC-27MAR26-70000-C-USDT
    symbol = contract.get("symbol", "")
    symbol_parts = symbol.split("-")
    strike = None
    expiration_date = None
    
    if len(symbol_parts) >= 3:
        try:
            strike_str = symbol_parts[2]
            # Убираем суффикс если есть (например, -USDT)
            strike_str = strike_str.split("-")[0]
            strike = int(strike_str)
        except (ValueError, IndexError):
            pass
    
    if delivery_ms:
        try:
            expiration_date = datetime.fromtimestamp(delivery_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        except (ValueError, OSError):
            pass
    
    # Определение статуса контракта
    status = contract.get("status", "")
    if status == "PreLaunch":
        contract_status = "PreLaunch"
    elif status == "Trading":
        contract_status = "Trading"
    elif status == "Delivering":
        contract_status = "Delivering"
    elif status == "Settled" or (days_to_expiry is not None and days_to_expiry <= 0):
        contract_status = "Closed"
    else:
        contract_status = status
    
    return {
        "symbol": symbol,
        "optionsType": contract.get("optionsType"),
        "strike": strike,
        "launch_time": launch_ms,
        "delivery_time": delivery_ms,
        "launch_date": datetime.fromtimestamp(launch_ms/1000, tz=timezone.utc).strftime("%Y-%m-%d") if launch_ms else None,
        "expiry_date": expiration_date,
        "original_duration_days": original_duration_days,
        "days_to_expiry": days_to_expiry,
        "period_type": period_type,
        "period_group": period_group,
        "delivery_fee_rate": float(contract.get("deliveryFeeRate", 0)),
        "is_daily_type": period_type in [OptionPeriodType.DAILY, OptionPeriodType.BI_DAILY, OptionPeriodType.TRI_DAILY],
        "status": contract_status,
        "raw_status": status,
    }


def classify_deribit_option(instrument: dict, reference_time: Optional[datetime] = None) -> dict:
    """
    Классифицировать опцион Deribit на основе settlement_period и длительности.
    
    Args:
        instrument: dict из API public/get_instruments
        reference_time: опционально, время для расчёта days_to_expiry
    
    Returns:
        dict с полной информацией о контракте включая классификацию
    """
    # Получаем timestamps
    expiration_ts = instrument.get("expiration_timestamp", 0)
    creation_ts = instrument.get("creation_timestamp", 0)
    
    # Settlement period определяет базовый тип
    settlement_period = instrument.get("settlement_period", "").lower()
    
    # Расчёт длительности
    if creation_ts and expiration_ts:
        original_duration_sec = (expiration_ts - creation_ts) / 1000
        original_duration_days = round(original_duration_sec / (60 * 60 * 24))
    else:
        original_duration_days = 0
    
    # Дни до экспирации
    now = reference_time or datetime.now(timezone.utc)
    if expiration_ts:
        expiration_dt = datetime.fromtimestamp(expiration_ts / 1000, tz=timezone.utc)
        days_to_expiry = max(0, (expiration_dt.date() - now.date()).days)
        expiration_date = expiration_dt.strftime("%Y-%m-%d")
    else:
        days_to_expiry = None
        expiration_date = None
    
    # Для Deribit settlement_period может быть: day, week, month, quarter
    # Но мы используем original_duration_days для более точной классификации
    if settlement_period == "day":
        # Day options обычно 1 день или меньше
        if original_duration_days <= 1:
            period_type = OptionPeriodType.DAILY
        elif original_duration_days == 2:
            period_type = OptionPeriodType.BI_DAILY
        elif original_duration_days == 3:
            period_type = OptionPeriodType.TRI_DAILY
        else:
            period_type = classify_by_original_duration(original_duration_days)
    elif settlement_period == "week":
        # Week options - используем длительность для уточнения
        period_type = classify_by_original_duration(original_duration_days)
        # Убеждаемся, что это weekly группа
        if period_type not in [OptionPeriodType.WEEKLY, OptionPeriodType.BI_WEEKLY, OptionPeriodType.TRI_WEEKLY]:
            # Если длительность не совпадает, используем фактическую
            period_type = classify_by_original_duration(original_duration_days)
    elif settlement_period == "month":
        period_type = classify_by_original_duration(original_duration_days)
    elif settlement_period == "quarter":
        period_type = OptionPeriodType.QUARTERLY
    else:
        # Fallback: классификация по длительности
        period_type = classify_by_original_duration(original_duration_days)
    
    period_group = PERIOD_GROUPS.get(period_type, "unknown")
    
    # Парсинг названия инструмента: BTC-27DEC24-80000-C
    name = instrument.get("instrument_name", "")
    parts = name.split("-") if name else []
    strike = instrument.get("strike")
    
    # Статус контракта
    is_active = instrument.get("is_active", True)
    if not is_active:
        contract_status = "Closed"
    elif days_to_expiry is not None and days_to_expiry == 0:
        contract_status = "Delivering"
    else:
        contract_status = "Trading"
    
    return {
        "symbol": name,
        "optionsType": instrument.get("option_type", "").upper(),
        "strike": strike,
        "launch_time": creation_ts,
        "delivery_time": expiration_ts,
        "launch_date": datetime.fromtimestamp(creation_ts/1000, tz=timezone.utc).strftime("%Y-%m-%d") if creation_ts else None,
        "expiry_date": expiration_date,
        "original_duration_days": original_duration_days,
        "days_to_expiry": days_to_expiry,
        "period_type": period_type,
        "period_group": period_group,
        "settlement_period": settlement_period,
        "is_daily_type": period_type in [OptionPeriodType.DAILY, OptionPeriodType.BI_DAILY, OptionPeriodType.TRI_DAILY],
        "status": contract_status,
        "raw_status": "active" if is_active else "inactive",
    }


def get_period_position_in_group(period_type: str) -> int:
    """
    Получить позицию периода внутри группы (0=nearest, 1=middle, 2=farthest).
    
    Args:
        period_type: Тип периода из OptionPeriodType
    
    Returns:
        Индекс позиции в группе
    """
    period_group = PERIOD_GROUPS.get(period_type)
    if not period_group:
        return -1
    
    order = PERIOD_ORDER_IN_GROUP.get(period_group, [])
    try:
        return order.index(period_type)
    except ValueError:
        return -1


def filter_contracts_by_period(
    contracts: list,
    period_group: str,
    position: str = "nearest"
) -> list:
    """
    Отфильтровать контракты по группе периодов и позиции.
    
    Args:
        contracts: Список контрактов с полями period_type, days_to_expiry
        period_group: Группа периодов ("daily", "weekly", "monthly")
        position: Позиция ("nearest", "middle", "farthest")
    
    Returns:
        Список контрактов выбранной позиции
    """
    # Фильтруем по группе периодов
    filtered = [c for c in contracts if PERIOD_GROUPS.get(c.get("period_type")) == period_group]
    
    if not filtered:
        return []
    
    # Группируем по уникальным period_type внутри группы
    period_types_in_group = PERIOD_ORDER_IN_GROUP.get(period_group, [])
    available_periods = sorted(
        set(c.get("period_type") for c in filtered),
        key=lambda x: period_types_in_group.index(x) if x in period_types_in_group else 999
    )
    
    # Выбираем позицию
    if position == "nearest":
        selected_period = available_periods[0]
    elif position == "farthest":
        selected_period = available_periods[-1]
    else:  # middle
        if len(available_periods) >= 3:
            selected_period = available_periods[1]
        elif len(available_periods) == 2:
            selected_period = available_periods[0]  # Ближе к middle
        else:
            selected_period = available_periods[0]
    
    # Возвращаем все контракты выбранного периода
    result = [c for c in filtered if c.get("period_type") == selected_period]
    
    # Сортируем по days_to_expiry, затем по strike
    result.sort(key=lambda x: (x.get("days_to_expiry") or 9999, x.get("strike") or 0))
    
    return result


def select_contract_by_period_and_position(
    contracts: list,
    period_group: str,
    position: str,
    option_type: Optional[str] = None
) -> Optional[dict]:
    """
    Выбрать один контракт по периоду, позиции и типу опциона.
    
    Args:
        contracts: Список контрактов
        period_group: Группа периодов ("daily", "weekly", "monthly")
        position: Позиция ("nearest", "middle", "farthest")
        option_type: Тип опциона ("Call", "Put") или None для любого
    
    Returns:
        Выбранный контракт или None
    """
    filtered = filter_contracts_by_period(contracts, period_group, position)
    
    if not filtered:
        return None
    
    # Фильтр по типу опциона
    if option_type:
        filtered = [c for c in filtered if c.get("optionsType", "").upper() == option_type.upper()]
    
    if not filtered:
        return None
    
    # Возвращаем первый (ближайший по expiry/strike)
    return filtered[0]
