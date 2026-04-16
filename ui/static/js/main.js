/**
 * Основной JavaScript для Web-GUI OptionsRunner.
 *
 * Функции:
 *   - Fetch запросы к API
 *   - Toast уведомления
 *   - Загрузка данных dashboard
 *   - Управление API ключами (mainnet / testnet / demo)
 */

// ─── Toast уведомления ──────────────────────────────────────────────

function showToast(title, message, type = 'info') {
    const toastEl = document.getElementById('toast');
    if (!toastEl) return;

    const titleEl = document.getElementById('toast-title');
    const bodyEl = document.getElementById('toast-body');

    titleEl.textContent = title;
    bodyEl.textContent = message;

    // Цвет заголовка
    const header = toastEl.querySelector('.toast-header');
    header.className = 'toast-header';
    if (type === 'success') header.classList.add('bg-success', 'text-white');
    else if (type === 'danger') header.classList.add('bg-danger', 'text-white');
    else if (type === 'warning') header.classList.add('bg-warning');

    const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
    toast.show();
}

// ─── API запросы ────────────────────────────────────────────────────

async function apiGet(url) {
    const res = await fetch(url);
    return res.json();
}

async function apiPost(url, body) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    return res.json();
}

async function apiDelete(url, params = {}) {
    const qs = new URLSearchParams(params).toString();
    const urlWithParams = qs ? `${url}?${qs}` : url;
    const res = await fetch(urlWithParams, { method: 'DELETE' });
    return res.json();
}

// ─── Dashboard данные ───────────────────────────────────────────────

async function loadDashboardData() {
    loadDashboardBalances();
    loadDashboardPositions();
    loadDashboardGreeks();
}

async function loadDashboardBalances() {
    const div = document.getElementById('balances-summary');
    if (!div) return;

    try {
        const [bybitRes, deribitRes] = await Promise.allSettled([
            fetch('/api/balances/bybit/summary').then(r => r.json()),
            fetch('/api/balances/deribit/summary').then(r => r.json()),
        ]);

        let html = '';

        if (bybitRes.status === 'fulfilled' && bybitRes.value.success) {
            const d = bybitRes.value.data;
            const equity = d.total_equity_usd || 0;
            html += `<div class="mb-2"><strong>Bybit:</strong> ${equity.toFixed(4)}</div>`;
        }

        if (deribitRes.status === 'fulfilled' && deribitRes.value.success) {
            const d = deribitRes.value.data;
            const equity = d.total_equity || 0;
            html += `<div><strong>Deribit:</strong> ${equity.toFixed(4)}</div>`;
        }

        div.innerHTML = html || '<p class="text-muted">Нет данных</p>';
    } catch (e) {
        div.innerHTML = '<p class="text-danger">Ошибка загрузки</p>';
    }
}

async function loadDashboardPositions() {
    const div = document.getElementById('positions-summary');
    if (!div) return;

    try {
        const [bybitRes, deribitRes] = await Promise.allSettled([
            fetch('/api/positions/bybit/summary').then(r => r.json()),
            fetch('/api/positions/deribit/summary').then(r => r.json()),
        ]);

        let totalPositions = 0;
        let totalPnl = 0;

        if (bybitRes.status === 'fulfilled' && bybitRes.value.success) {
            totalPositions += bybitRes.value.data.total_positions || 0;
            totalPnl += bybitRes.value.data.total_unrealized_pnl || 0;
        }

        if (deribitRes.status === 'fulfilled' && deribitRes.value.success) {
            totalPositions += deribitRes.value.data.total_positions || 0;
            totalPnl += deribitRes.value.data.total_unrealized_pnl || 0;
        }

        const pnlClass = totalPnl >= 0 ? 'text-success' : 'text-danger';
        div.innerHTML = `
            <div class="mb-2"><strong>Позиций:</strong> ${totalPositions}</div>
            <div class="${pnlClass}"><strong>P&L:</strong> ${totalPnl.toFixed(4)}</div>
        `;
    } catch (e) {
        div.innerHTML = '<p class="text-danger">Ошибка загрузки</p>';
    }
}

async function loadDashboardGreeks() {
    const div = document.getElementById('greeks-summary');
    if (!div) return;

    try {
        const [bybitRes, deribitRes] = await Promise.allSettled([
            fetch('/api/positions/bybit/summary').then(r => r.json()),
            fetch('/api/positions/deribit/summary').then(r => r.json()),
        ]);

        let delta = 0, gamma = 0, theta = 0, vega = 0;

        if (bybitRes.status === 'fulfilled' && bybitRes.value.success) {
            const d = bybitRes.value.data;
            delta += d.total_delta || 0;
            gamma += d.total_gamma || 0;
            theta += d.total_theta || 0;
            vega += d.total_vega || 0;
        }

        if (deribitRes.status === 'fulfilled' && deribitRes.value.success) {
            const d = deribitRes.value.data;
            delta += d.total_delta || 0;
            gamma += d.total_gamma || 0;
            theta += d.total_theta || 0;
            vega += d.total_vega || 0;
        }

        div.innerHTML = `
            <div class="row text-center">
                <div class="col-6 mb-2"><strong>Δ</strong> ${delta.toFixed(4)}</div>
                <div class="col-6 mb-2"><strong>Γ</strong> ${gamma.toFixed(4)}</div>
                <div class="col-6"><strong>Θ</strong> ${theta.toFixed(4)}</div>
                <div class="col-6"><strong>V</strong> ${vega.toFixed(4)}</div>
            </div>
        `;
    } catch (e) {
        div.innerHTML = '<p class="text-danger">Ошибка загрузки</p>';
    }
}

// ─── Переключение сети из навбара ──────────────────────────────────

async function toggleNetwork(exchange) {
    const badge = document.getElementById(`${exchange}-network`);
    if (!badge) return;

    const currentText = badge.textContent.trim().toLowerCase();

    let newTestnet;
    if (exchange === 'bybit') {
        newTestnet = currentText !== 'demo';
    } else {
        newTestnet = currentText !== 'testnet';
    }

    try {
        const response = await fetch('/api/keys/network', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ exchange, testnet: newTestnet }),
        });

        const result = await response.json();

        if (result.success) {
            updateNetworkBadge(exchange, newTestnet);
            showToast('Сеть изменена', result.message, 'success');
            setTimeout(() => {
                window.location.reload();
            }, 500);
        } else {
            showToast('Ошибка', result.error, 'danger');
        }
    } catch (error) {
        showToast('Ошибка', error.message, 'danger');
    }
}

// ─── Обновление бейджей сети (доступно на ВСЕХ страницах) ──────────

const NETWORK_URLS = {
    bybit: {
        demo: 'https://api-demo.bybit.com',
        mainnet: 'https://api.bybit.com',
    },
    deribit: {
        testnet: 'https://test.deribit.com/api/v2',
        mainnet: 'https://www.deribit.com/api/v2',
    },
};

function updateNetworkBadge(exchange, testnet) {
    // Единый ID для ВСЕХ страниц (из макроса network_badges)
    const badge = document.getElementById(`${exchange}-network`);
    if (!badge) return;

    let network;
    if (exchange === 'bybit') {
        network = testnet ? 'demo' : 'mainnet';
    } else {
        network = testnet ? 'testnet' : 'mainnet';
    }

    badge.textContent = network;

    // Цвет
    let colorClass;
    if (exchange === 'bybit' && testnet) {
        colorClass = 'bg-warning text-dark';
    } else if (testnet) {
        colorClass = 'bg-info text-white';
    } else {
        colorClass = 'bg-success text-white';
    }
    badge.className = `network-badge clickable ${colorClass}`;
}

function updateNetworkUrl(exchange, testnet) {
    const urlEl = document.getElementById(`${exchange}-url`);
    if (urlEl) {
        const urls = NETWORK_URLS[exchange];
        if (exchange === 'bybit' && testnet) {
            urlEl.textContent = urls.demo;
        } else {
            urlEl.textContent = testnet ? urls.testnet : urls.mainnet;
        }
    }
}

function updateAllNetworkBadges(exchange, testnet) {
    updateNetworkBadge(exchange, testnet);
}

// ─── Инициализация бейджей на всех страницах ───────────────────────
// Бейджи уже отрендерены Jinja из .env файла — НЕ перезаписываем их.
// updateNetworkBadge вызывается ТОЛЬКО при клике пользователя.

// ─── API Keys страница ──────────────────────────────────────────────

async function loadApiKeysPage() {
    // Загрузка маскированных ключей (включая .env инфо)
    const data = await apiGet('/api/keys');
    if (data.success) {
        populateExchangeFields('bybit', data.data.bybit);
        populateExchangeFields('deribit', data.data.deribit);
    }

    // Бейджи уже установлены из Jinja шаблона — не перезаписываем
    // Только загружаем URL для каждой сети
    loadNetworkUrl('bybit');
    loadNetworkUrl('deribit');
}

function populateExchangeFields(exchange, info) {
    // Отладка
    console.log(`[${exchange}] populateExchangeFields:`, info);

    // .env ключи (mainnet) — показываем всегда
    setEl(`${exchange}-env-api-key`, info.env_api_key || '—');
    setEl(`${exchange}-env-api-secret`, info.env_api_secret || '—');

    // .env Demo ключи (только Bybit)
    if (exchange === 'bybit') {
        setEl(`${exchange}-env-demo-api-key`, info.env_demo_api_key || '—');
        setEl(`${exchange}-env-demo-api-secret`, info.env_demo_api_secret || '—');
    }

    // Сохранённые ключи — Mainnet
    if (info.mainnet && info.mainnet.configured) {
        setEl(`${exchange}-mainnet-api-key`, info.mainnet.api_key);
        setEl(`${exchange}-mainnet-api-secret`, info.mainnet.api_secret);
    }

    // Сохранённые ключи — Testnet
    if (info.testnet && info.testnet.configured) {
        setEl(`${exchange}-testnet-api-key`, info.testnet.api_key);
        setEl(`${exchange}-testnet-api-secret`, info.testnet.api_secret);
    }

    // Сохранённые ключи — Demo
    if (info.demo && info.demo.configured) {
        setEl(`${exchange}-demo-api-key`, info.demo.api_key);
        setEl(`${exchange}-demo-api-secret`, info.demo.api_secret);
    }

    // Use Main As Test флаг
    const useMainAsTestCheckbox = document.getElementById(`${exchange}-use-main-as-test`);
    if (useMainAsTestCheckbox) {
        useMainAsTestCheckbox.checked = info.use_main_as_test || false;
    }

    // Бейдж НЕ трогаем — он уже правильно установлен Jinja из .env
}

function setEl(id, value) {
    const el = document.getElementById(id);
    if (el) {
        if (el.tagName === 'INPUT') {
            el.value = value;
        } else {
            el.textContent = value;
        }
    }
}

async function loadNetworkUrl(exchange) {
    const data = await apiGet(`/api/keys/network/${exchange}`);
    if (data.success) {
        const d = data.data;
        const urlEl = document.getElementById(`${exchange}-url`);
        if (urlEl) {
            const badge = document.getElementById(`${exchange}-network`);
            const currentText = badge ? badge.textContent.trim().toLowerCase() : 'mainnet';
            const isTestnet = currentText === 'demo' || currentText === 'testnet';

            if (exchange === 'bybit') {
                urlEl.textContent = isTestnet ? NETWORK_URLS.bybit.demo : NETWORK_URLS.bybit.mainnet;
            } else {
                urlEl.textContent = isTestnet ? NETWORK_URLS.deribit.testnet : NETWORK_URLS.deribit.mainnet;
            }
        }
    }
}

async function saveKeys(exchange, testnet, isDemo) {
    const suffix = isDemo ? 'demo' : (testnet ? 'testnet' : 'mainnet');
    const apiKey = document.getElementById(`${exchange}-${suffix}-api-key`).value.trim();
    const apiSecret = document.getElementById(`${exchange}-${suffix}-api-secret`).value.trim();

    if (!apiKey || !apiSecret) {
        showToast('Ошибка', 'Заполните оба поля (ключ и секрет)', 'danger');
        return;
    }

    const data = await apiPost('/api/keys', {
        exchange,
        api_key: apiKey,
        api_secret: apiSecret,
        testnet: testnet,
    });

    if (data.success) {
        const netLabel = isDemo ? 'demo' : (testnet ? 'testnet' : 'mainnet');
        showToast('Сохранено', `Ключи ${netLabel} для ${exchange} сохранены`, 'success');
        // Обновляем поля
        setEl(`${exchange}-${suffix}-api-key`, apiKey.substring(0, 4) + '****');
        setEl(`${exchange}-${suffix}-api-secret`, '****' + apiSecret.slice(-4));
        loadNetworkStatus(exchange);
    } else {
        showToast('Ошибка', data.error, 'danger');
    }
}

async function testConnection(exchange, testnet, isDemo) {
    const suffix = isDemo ? 'demo' : (testnet ? 'testnet' : 'mainnet');
    const apiKey = document.getElementById(`${exchange}-${suffix}-api-key`).value.trim();
    const apiSecret = document.getElementById(`${exchange}-${suffix}-api-secret`).value.trim();

    if (!apiKey || !apiSecret) {
        showToast('Ошибка', 'Сначала введите ключи', 'danger');
        return;
    }

    const statusDiv = document.getElementById(`${exchange}-${suffix}-status`);
    if (statusDiv) {
        statusDiv.innerHTML = '<div class="spinner-border spinner-border-sm"></div> Тестирование...';
    }

    const data = await apiPost('/api/keys/test', {
        exchange,
        api_key: apiKey,
        api_secret: apiSecret,
        testnet: testnet,
        is_demo: isDemo,
    });

    if (data.success) {
        if (statusDiv) {
            statusDiv.innerHTML = `<div class="alert alert-success py-1"><i class="bi bi-check-circle"></i> ${data.message}</div>`;
        }
        showToast('Успех', data.message, 'success');
    } else {
        if (statusDiv) {
            statusDiv.innerHTML = `<div class="alert alert-danger py-1"><i class="bi bi-x-circle"></i> ${data.message}</div>`;
        }
        showToast('Ошибка', data.message, 'danger');
    }
}

async function deleteSavedKeys(exchange, testnet, isDemo = false) {
    let netLabel;
    if (isDemo) {
        netLabel = 'demo';
    } else if (testnet === true) {
        netLabel = 'testnet';
    } else if (testnet === false) {
        netLabel = 'mainnet';
    } else {
        netLabel = 'все сети';
    }

    if (!confirm(`Удалить сохранённые ключи ${exchange} (${netLabel})?`)) return;

    const params = {};
    if (isDemo) {
        params.is_demo = 'true';
    } else if (testnet !== null) {
        params.testnet = testnet.toString();
    }

    const data = await apiDelete(`/api/keys/${exchange}`, params);
    if (data.success) {
        const suffix = isDemo ? 'demo' : (testnet === true ? 'testnet' : (testnet === false ? 'mainnet' : null));
        if (suffix) {
            setEl(`${exchange}-${suffix}-api-key`, '');
            setEl(`${exchange}-${suffix}-api-secret`, '');
        }
        showToast('Удалено', `Ключи ${exchange} (${netLabel}) удалены`, 'success');
        loadNetworkStatus(exchange);
    }
}

async function switchNetwork(exchange, testnet) {
    // Для Bybit: testnet switch = demo режим
    const isBybitDemo = exchange === 'bybit' && testnet;

    const data = await apiPost('/api/keys/network', { exchange, testnet: isBybitDemo });
    if (data.success) {
        updateAllNetworkBadges(exchange, testnet);
        showToast('Сеть изменена', data.message, 'success');
        // Перезагружаем страницу чтобы данные обновились из нового .env
        setTimeout(() => {
            window.location.reload();
        }, 500);
    }
}

async function toggleUseMainAsTest(exchange, value) {
    const data = await apiPost('/api/keys/use-main-as-test', {
        exchange,
        use_main_as_test: value,
    });

    if (data.success) {
        const status = value ? 'включён' : 'выключен';
        showToast('Use Main As Test', `${exchange} — ${status}`, 'success');
    } else {
        showToast('Ошибка', data.error, 'danger');
        // Восстанавливаем положение
        const checkbox = document.getElementById(`${exchange}-use-main-as-test`);
        if (checkbox) checkbox.checked = !value;
    }
}

function updateAllNetworkBadges(exchange, testnet) {
    updateNetworkBadge(exchange, testnet);

    // Обновляем бейдж в навбаре dashboard
    const dashBadge = document.getElementById(`${exchange}-network`);
    if (dashBadge) {
        if (exchange === 'bybit') {
            dashBadge.textContent = testnet ? 'demo' : 'mainnet';
        } else {
            dashBadge.textContent = testnet ? 'testnet' : 'mainnet';
        }
    }
}
