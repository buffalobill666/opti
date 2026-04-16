/**
 * JavaScript для страницы ордеров OptionsRunner.
 *
 * Функции:
 *   - Переключение биржи
 *   - Загрузка инструментов по активу/периоду/позиции
 *   - Создание ордера
 *   - Загрузка и отмена ордеров
 */

let currentExchange = 'bybit';

// ─── Инициализация ──────────────────────────────────────────────────

function initOrdersPage() {
    bindFormDynamics();
    loadOrders();
}

function bindFormDynamics() {
    // Other актив -> показать поле тикера
    document.querySelectorAll('input[name="asset"]').forEach(radio => {
        radio.addEventListener('change', () => {
            const isOther = document.getElementById('asset-other').checked;
            document.getElementById('custom-asset').style.display = isOther ? '' : 'none';
            // Сбросить список инструментов при смене актива
            resetInstruments();
        });
    });

    // Цена — подсказка валюты
    document.getElementById('price-currency').addEventListener('change', () => {
        const cur = document.getElementById('price-currency').value;
        document.getElementById('price-hint').textContent = cur === 'USDT' ? 'Цена в USDT' : 'Цена в активе';
    });

    // Отправка формы
    document.getElementById('order-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await submitOrder();
    });
}

// ─── Переключение биржи ─────────────────────────────────────────────

function setExchange(exchange) {
    currentExchange = exchange;

    // Обновить кнопки
    document.getElementById('btn-bybit').classList.toggle('active', exchange === 'bybit');
    document.getElementById('btn-deribit').classList.toggle('active', exchange === 'deribit');

    // Сбросить инструменты
    resetInstruments();

    // Перезагрузить ордера
    loadOrders();
}

function resetInstruments() {
    const select = document.getElementById('order-symbol');
    select.innerHTML = '<option value="">— Сначала найдите инструменты —</option>';
    document.getElementById('instruments-count').style.display = 'none';
}

// ─── Загрузка инструментов ──────────────────────────────────────────

async function loadInstruments() {
    const asset = getSelectedAsset();
    const period = document.querySelector('input[name="period"]:checked').value;
    const position = document.querySelector('input[name="position"]:checked').value;
    const opt = document.querySelector('input[name="option-side"]:checked')?.value || 'Call';
    const optionType = opt === 'Put' ? 'P' : 'C';

    if (!asset) {
        showToast('Ошибка', 'Выберите актив или введите тикер', 'danger');
        return;
    }

    const loading = document.getElementById('instruments-loading');
    const countDiv = document.getElementById('instruments-count');
    const select = document.getElementById('order-symbol');

    loading.style.display = '';
    countDiv.style.display = 'none';
    select.innerHTML = '<option value="">Загрузка...</option>';

    try {
        const url = `/api/orders/${currentExchange}/instruments?asset=${encodeURIComponent(asset)}&period=${period}&position=${position}&option_type=${optionType}`;
        const res = await fetch(url);
        const data = await res.json();

        loading.style.display = 'none';

        if (!data.success) {
            select.innerHTML = '<option value="">Ошибка загрузки</option>';
            showToast('Ошибка', data.error, 'danger');
            return;
        }

        const instruments = data.data.instruments || [];

        if (instruments.length === 0) {
            select.innerHTML = '<option value="">Нет инструментов</option>';
            showToast('Инструменты', 'Не найдено инструментов для выбранных параметров', 'warning');
            return;
        }

        // Заполняем выпадающий список
        let html = '';
        for (const inst of instruments) {
            const days = inst.days_to_expiry;
            const daysLabel = days !== null ? `${days}д` : '?';
            const typeLabel = inst.option_type === 'C' ? 'C' : (inst.option_type === 'P' ? 'P' : '');
            const strikeLabel = inst.strike ? inst.strike.toLocaleString() : '';

            const label = `${inst.symbol}  |  ${strikeLabel} ${typeLabel}  |  ${daysLabel}д`;
            html += `<option value="${inst.symbol}">${label}</option>`;
        }
        select.innerHTML = html;

        // Показать количество
        countDiv.textContent = `Найдено: ${instruments.length}`;
        countDiv.style.display = '';

    } catch (e) {
        loading.style.display = 'none';
        select.innerHTML = '<option value="">Ошибка сети</option>';
        showToast('Ошибка', e.message, 'danger');
    }
}

function getSelectedAsset() {
    const selected = document.querySelector('input[name="asset"]:checked');
    if (selected.value) return selected.value;  // BTC или ETH

    // Other — читаем кастомный тикер
    const custom = document.getElementById('custom-asset').value.trim().toUpperCase();
    return custom || null;
}

// ─── Создание ордера ────────────────────────────────────────────────

async function submitOrder() {
    const symbol = document.getElementById('order-symbol').value;
    if (!symbol) {
        showToast('Ошибка', 'Выберите инструмент', 'danger');
        return;
    }

    const optionSide = document.querySelector('input[name="option-side"]:checked').value;
    const tradeSide = document.getElementById('order-side').value;
    const orderType = document.getElementById('order-type').value;
    const qty = document.getElementById('order-qty').value;
    const price = document.getElementById('order-price').value;
    const tif = document.getElementById('order-tif').value;
    const reduceOnly = document.getElementById('order-reduce-only')?.checked || false;
    const orderLinkId = document.getElementById('order-link-id')?.value?.trim() || null;
    const tp = document.getElementById('order-tp')?.value || null;
    const sl = document.getElementById('order-sl')?.value || null;
    const postOnly = document.getElementById('order-post-only')?.checked ?? true;
    const label = document.getElementById('order-label')?.value?.trim() || null;

    // Для Deribit — side = buy/sell, для Bybit — Buy/Sell
    const effectiveSide = currentExchange === 'deribit' ? tradeSide.toLowerCase() : tradeSide;

    const body = {
        exchange: currentExchange,
        symbol: symbol,
        side: effectiveSide,
        order_type: orderType,
        qty: qty,
        price: price || null,
        time_in_force: tif,
        order_link_id: orderLinkId,
        reduce_only: reduceOnly,
        take_profit: tp,
        stop_loss: sl,
        post_only: postOnly,
        label: label,
    };

    try {
        const res = await fetch(`/api/orders/${currentExchange}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await res.json();

        if (data.success) {
            showToast('Ордер создан', `ID: ${data.data.order_id}`, 'success');
            loadOrders();
        } else {
            showToast('Ошибка', data.error, 'danger');
        }
    } catch (e) {
        showToast('Ошибка', e.message, 'danger');
    }
}

// ─── Загрузка ордеров ───────────────────────────────────────────────

async function loadOrders() {
    const tbody = document.getElementById('orders-tbody');
    tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted"><div class="spinner-border spinner-border-sm"></div></td></tr>';

    try {
        const res = await fetch(`/api/orders/${currentExchange}`);
        const data = await res.json();

        if (!data.success || !data.data.orders || data.data.orders.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">Нет активных ордеров</td></tr>';
            return;
        }

        tbody.innerHTML = data.data.orders.map(o => {
            const sideLower = (o.side || '').toLowerCase();
            const sideClass = sideLower === 'buy' ? 'text-success' : 'text-danger';

            return `
                <tr>
                    <td><small title="${o.order_id || ''}">${(o.order_id || '-').substring(0, 12)}...</small></td>
                    <td><strong>${o.symbol || o.instrument_name || '-'}</strong></td>
                    <td class="${sideClass}">${o.side}</td>
                    <td>${o.order_type}</td>
                    <td>${o.qty || '-'}</td>
                    <td>${o.price || '-'}</td>
                    <td>${o.status || o.order_status || '-'}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-danger" onclick="cancelOrder('${o.order_id}')">
                            <i class="bi bi-x-circle"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger">Ошибка загрузки</td></tr>`;
    }
}

// ─── Отмена ордера ──────────────────────────────────────────────────

async function cancelOrder(orderId) {
    if (!confirm('Отменить ордер?')) return;

    try {
        const res = await fetch(`/api/orders/${currentExchange}/${orderId}`, { method: 'DELETE' });
        const data = await res.json();

        if (data.success) {
            showToast('Ордер отменён', orderId.substring(0, 12) + '...', 'success');
            loadOrders();
        } else {
            showToast('Ошибка', data.error, 'danger');
        }
    } catch (e) {
        showToast('Ошибка', e.message, 'danger');
    }
}
