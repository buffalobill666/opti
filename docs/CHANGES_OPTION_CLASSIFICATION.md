# 🔄 Изменения системы классификации опционов

## Обзор изменений

Переход от относительной классификации ("ближайший/мидл/дальний") к **9 конкретным типам периодов** на основе оригинальной длительности контракта.

---

## 📊 9 типов опционных контрактов

### Daily Group (дневные)
| Тип | Длительность | Описание |
|-----|--------------|----------|
| `Daily` | 1 день | Экспирация через 1 день |
| `Bi-Daily` | 2 дня | Экспирация через 2 дня |
| `Tri-Daily` | 3 дня | Экспирация через 3 дня |

### Weekly Group (недельные)
| Тип | Длительность | Описание |
|-----|--------------|----------|
| `Weekly` | 4-7 дней | Недельная экспирация |
| `Bi-Weekly` | 8-14 дней | Двухнедельная экспирация |
| `Tri-Weekly` | 15-21 дней | Трёхнедельная экспирация |

### Monthly Group (месячные)
| Тип | Длительность | Описание |
|-----|--------------|----------|
| `Monthly` | 22-31 дней | Месячная экспирация |
| `Bi-Monthly` | 32-62 дней | Двухмесячная экспирация |
| `Quarterly` | > 62 дней | Квартальная экспирация |

---

## 🔑 Ключевые изменения

### 1. Классификация по `original_duration_days`
**Было:** Классификация по `days_to_expiry` (дни до экспирации от текущего момента)  
**Стало:** Классификация по `original_duration_days` = `(deliveryTime - launchTime) / 86400000`

**Преимущества:**
- ✅ Тип контракта не меняется со временем
- ✅ Корректное определение комиссии доставки (deliveryFeeRate)
- ✅ Нет смещения классификации при приближении экспирации

### 2. Статусная модель контрактов
| Статус | Описание | Допуск к ордерам |
|--------|----------|------------------|
| `PreLaunch` | Контракт ещё не торгуется | ❌ Нет |
| `Trading` | Активная торговля | ✅ Да |
| `Delivering` | Идёт процесс экспирации | ❌ Нет |
| `Closed` | Торги закрыты | ❌ Нет |

### 3. Кэширование инструментов
- **Первичная загрузка:** При старте бота
- **Обновление:** Ежедневно в 08:01 UTC (после листинга новых контрактов)
- **Фильтрация:** Только контракты со статусом `Trading`

---

## 📁 Новые файлы

### `/workspace/utils/option_classifier.py`
Центральный модуль классификации с функциями:
- `classify_by_original_duration()` — базовая классификация
- `classify_bybit_option()` — классификация Bybit контрактов
- `classify_deribit_option()` — классификация Deribit контрактов
- `filter_contracts_by_period()` — фильтрация по группе и позиции
- `select_contract_by_period_and_position()` — выбор одного контракта

### Константы
```python
class OptionPeriodType:
    DAILY = "Daily"
    BI_DAILY = "Bi-Daily"
    TRI_DAILY = "Tri-Daily"
    WEEKLY = "Weekly"
    BI_WEEKLY = "Bi-Weekly"
    TRI_WEEKLY = "Tri-Weekly"
    MONTHLY = "Monthly"
    BI_MONTHLY = "Bi-Monthly"
    QUARTERLY = "Quarterly"

PERIOD_GROUPS = {
    "Daily": "daily", "Bi-Daily": "daily", "Tri-Daily": "daily",
    "Weekly": "weekly", "Bi-Weekly": "weekly", "Tri-Weekly": "weekly",
    "Monthly": "monthly", "Bi-Monthly": "monthly", "Quarterly": "monthly",
}

PERIOD_ORDER_IN_GROUP = {
    "daily": ["Daily", "Bi-Daily", "Tri-Daily"],
    "weekly": ["Weekly", "Bi-Weekly", "Tri-Weekly"],
    "monthly": ["Monthly", "Bi-Monthly", "Quarterly"],
}
```

---

## 🛠️ Обновлённые файлы

### `/workspace/ui/models.py`
Добавлен новый Enum:
```python
class ContractPeriodType(str, Enum):
    """Конкретный тип периода контракта (9 типов)."""
    DAILY = "Daily"
    BI_DAILY = "Bi-Daily"
    # ... все 9 типов
```

### `/workspace/ui/api/orders_routes.py`
- `_parse_deribit_instrument()` — обновлено для использования классификатора
- `_classify_period_detailed()` — новая функция детальной классификации
- `_select_by_expiration()` — переписано для работы с 9 типами
- Парсинг инструментов теперь включает поля:
  - `period_type` — конкретный тип (9 типов)
  - `period_group` — группа (daily/weekly/monthly)
  - `original_duration_days` — оригинальная длительность

---

## 🧪 Тестирование

### Пример использования
```python
from utils.option_classifier import filter_contracts_by_period, OptionPeriodType

# Фильтрация daily группы
daily_nearest = filter_contracts_by_period(contracts, 'daily', 'nearest')
# Возвращает контракты типа Daily

daily_middle = filter_contracts_by_period(contracts, 'daily', 'middle')
# Возвращает контракты типа Bi-Daily

daily_farthest = filter_contracts_by_period(contracts, 'daily', 'farthest')
# Возвращает контракты типа Tri-Daily
```

### Результаты тестов
```
=== Daily Group ===
Nearest: BTC-16APR25   (Daily)
Middle:  BTC-17APR25   (Bi-Daily)
Farthest: BTC-18APR25  (Tri-Daily)

=== Weekly Group ===
Nearest: BTC-21APR25   (Weekly)
Middle:  BTC-28APR25   (Bi-Weekly)
Farthest: BTC-05MAY25  (Tri-Weekly)

=== Monthly Group ===
Nearest: BTC-30MAY25   (Monthly)
Middle:  BTC-27JUN25   (Bi-Monthly)
Farthest: BTC-26SEP25  (Quarterly)
```

---

## 📋 Следующие шаги

### Этап 1: ✅ Завершён
- [x] Создание `utils/option_classifier.py`
- [x] Обновление `ui/models.py`
- [x] Обновление `ui/api/orders_routes.py`
- [x] Тестирование классификации

### Этап 2: Интеграция в клиентский слой
- [ ] Обновление `client/main_client.py` для поддержки классификации
- [ ] Обновление функций получения инструментов Bybit/Deribit
- [ ] Добавление фильтрации по статусу `Trading`

### Этап 3: Система кэширования
- [ ] Создание `client/market_data_cache.py`
- [ ] Реализация загрузки при старте
- [ ] Планировщик обновления на 08:01 UTC
- [ ] Фильтрация по статусам

### Этап 4: Безопасность ордеров
- [ ] Проверка статуса контракта перед отправкой ордера
- [ ] Блокировка операций на не-`Trading` контрактах
- [ ] Валидация в webhook handlers

### Этап 5: UI обновления
- [ ] Отображение `period_type` в интерфейсе
- [ ] Обновление форм создания стратегий
- [ ] Документация для пользователя

---

## ⚠️ Breaking Changes

### API изменения
Поле `period` в ответах API теперь содержит **группу** (`daily`/`weekly`/`monthly`)  
Добавлено новое поле `period_type` с **конкретным типом** (9 значений)

### Миграция стратегий
Старые стратегии с `ContractPeriod` требуют обновления:
```python
# Было
contracts: [
    {"period": "daily", "position": "nearest"}
]

# Стало (совместимо обратно)
contracts: [
    {"period": "daily", "position": "nearest"}  # period теперь группа
]
```

---

## 📚 Документация

- [Исследование проблемы](docs/option_classification_research.md)
- [API Reference](docs/api_reference.md)
- [Migration Guide](docs/migration_guide.md)
