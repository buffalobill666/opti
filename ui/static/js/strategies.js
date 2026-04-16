/**
 * JavaScript для управления стратегиями OptionsRunner.
 *
 * Функции:
 *   - Загрузка списка стратегий
 *   - Загрузка детальной информации стратегии
 *   - Создание / редактирование / удаление стратегий
 *   - Динамика формы (показ/скрытие полей)
 */

// ─── Утилиты ────────────────────────────────────────────────────────

function formatDateTime(isoStr) {
    if (!isoStr) return '—';
    const d = new Date(isoStr);
    return d.toLocaleString('ru-RU', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ─── Список стратегий ───────────────────────────────────────────────

let deleteTargetId = null;

async function loadStrategiesList() {
    const div = document.getElementById('strategies-list');
    if (!div) return;

    try {
        const res = await fetch('/api/strategies');
        const data = await res.json();

        if (!data.success) {
            div.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> ${escapeHtml(data.error)}</div>`;
            return;
        }

        const strategies = data.data || [];

        if (strategies.length === 0) {
            div.innerHTML = `
                <div class="card">
                    <div class="card-body text-center py-5">
                        <i class="bi bi-diagram-3" style="font-size: 3rem; color: var(--text-muted);"></i>
                        <h5 class="mt-3">Нет стратегий</h5>
                        <p class="text-muted">Создайте первую стратегию для начала работы</p>
                        <a href="/strategies/new" class="btn btn-primary btn-sm">
                            <i class="bi bi-plus-circle"></i> Создать стратегию
                        </a>
                    </div>
                </div>
            `;
            return;
        }

        let html = '<div class="row g-3">';
        for (const s of strategies) {
            const statusBadge = s.is_active
                ? '<span class="badge bg-success">Активна</span>'
                : '<span class="badge bg-secondary">Неактивна</span>';

            const assetLabel = s.asset_type === 'Other'
                ? escapeHtml(s.custom_asset || 'Other')
                : escapeHtml(s.asset_type);

            const entryTypeColor = s.entry_type === 'Call' ? 'success' : (s.entry_type === 'Put' ? 'danger' : 'warning');
            const entryBadge = `<span class="badge bg-${entryTypeColor}">${escapeHtml(s.entry_type)}</span>`;

            const volumeLabel = s.volume_currency === 'USDT'
                ? `${s.volume} USDT`
                : `${s.volume} ${assetLabel}`;

            const splitLabel = s.volume_split
                ? `<br><small class="text-muted">÷ ${s.split_count} контрактов</small>`
                : '';

            const contractsLabel = s.contracts && s.contracts.length > 0
                ? `<br><small class="text-muted">${s.contracts.map(c => `${c.period}:${c.position}`).join(', ')}</small>`
                : '';

            html += `
                <div class="col-md-6 col-lg-4">
                    <div class="card strategy-card" style="cursor: pointer;" onclick="window.location.href='/strategies/${s.id}'">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <span>${escapeHtml(s.name)}</span>
                            ${statusBadge}
                        </div>
                        <div class="card-body">
                            <div class="mb-2">
                                <small class="text-muted">Актив:</small> ${assetLabel}
                            </div>
                            <div class="mb-2">
                                <small class="text-muted">Вход:</small> ${entryBadge}
                            </div>
                            <div class="mb-2">
                                <small class="text-muted">Объём:</small> ${volumeLabel}${splitLabel}${contractsLabel}
                            </div>
                            ${s.description ? `<div class="mb-2"><small class="text-muted">${escapeHtml(s.description)}</small></div>` : ''}
                            <div class="d-flex justify-content-between mt-3">
                                <small class="text-muted" title="Создана">${formatDateTime(s.created_at)}</small>
                                <div class="d-flex gap-1" onclick="event.stopPropagation();">
                                    <button class="btn btn-outline-primary btn-sm" onclick="window.location.href='/strategies/${s.id}/edit'" title="Редактировать">
                                        <i class="bi bi-pencil"></i>
                                    </button>
                                    <button class="btn btn-outline-danger btn-sm" onclick="confirmDelete('${s.id}', '${escapeHtml(s.name)}')" title="Удалить">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        html += '</div>';
        div.innerHTML = html;

    } catch (e) {
        div.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Ошибка загрузки: ${escapeHtml(e.message)}</div>`;
    }
}

// ─── Детальная информация стратегии ─────────────────────────────────

async function loadStrategyDetail(strategyId) {
    const div = document.getElementById('strategy-detail');
    if (!div) return;

    try {
        const res = await fetch(`/api/strategies/${strategyId}`);
        const data = await res.json();

        if (!data.success) {
            div.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> ${escapeHtml(data.error)}</div>`;
            return;
        }

        const s = data.data;
        const editBtn = document.getElementById('edit-btn');
        if (editBtn) editBtn.style.display = '';

        const assetLabel = s.asset_type === 'Other'
            ? escapeHtml(s.custom_asset || 'Other')
            : escapeHtml(s.asset_type);

        const entryTypeColor = s.entry_type === 'Call' ? 'success' : (s.entry_type === 'Put' ? 'danger' : 'warning');

        const volumeLabel = s.volume_currency === 'USDT'
            ? `${s.volume} USDT`
            : `${s.volume} ${assetLabel}`;

        const splitLabel = s.volume_split
            ? `<span class="badge bg-info">Разделён на ${s.split_count}</span>`
            : '';

        // Контракты
        let contractsHtml = '<span class="text-muted">Не выбраны</span>';
        if (s.contracts && s.contracts.length > 0) {
            contractsHtml = '<div class="d-flex flex-wrap gap-2">';
            for (const c of s.contracts) {
                const periodLabels = { daily: 'Дневной', weekly: 'Неделя', monthly: 'Месяц' };
                const posLabels = { nearest: 'Ближний', middle: 'Мидл', farthest: 'Дальний' };
                contractsHtml += `<span class="badge bg-primary">${periodLabels[c.period] || c.period}: ${posLabels[c.position] || c.position}</span>`;
            }
            contractsHtml += '</div>';
        }

        // SL / TP
        const slHtml = renderTriggerInfo('StopLoss', s.stop_loss, 'bi-shield-x', 'danger');
        const tpHtml = renderTriggerInfo('TakeProfit', s.take_profit, 'bi-graph-up-arrow', 'success');

        // Webhook входа
        const entryWebhookHtml = s.entry_webhook && s.entry_webhook.enabled
            ? `<div class="mb-2"><i class="bi bi-webhook"></i> Webhook: <strong>${escapeHtml(s.entry_webhook.name)}</strong></div>`
            : '';

        html = `
            <div class="row g-3">
                <!-- Основная информация -->
                <div class="col-12">
                    <div class="card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <span><i class="bi bi-info-circle"></i> Основная информация</span>
                            ${s.is_active ? '<span class="badge bg-success">Активна</span>' : '<span class="badge bg-secondary">Неактивна</span>'}
                        </div>
                        <div class="card-body">
                            <h5>${escapeHtml(s.name)}</h5>
                            ${s.description ? `<p class="text-muted">${escapeHtml(s.description)}</p>` : ''}
                            <div class="row g-2 mt-2">
                                <div class="col-md-4"><small class="text-muted">Создана:</small> ${formatDateTime(s.created_at)}</div>
                                <div class="col-md-4"><small class="text-muted">Обновлена:</small> ${formatDateTime(s.updated_at)}</div>
                                <div class="col-md-4"><small class="text-muted">ID:</small> <code>${s.id}</code></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Параметры -->
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header"><i class="bi bi-currency-bitcoin"></i> Актив и Объём</div>
                        <div class="card-body">
                            <div class="mb-2"><strong>Актив:</strong> ${assetLabel}</div>
                            <div class="mb-2"><strong>Объём:</strong> ${volumeLabel} ${splitLabel}</div>
                            <div class="mb-2"><strong>Тип входа:</strong> <span class="badge bg-${entryTypeColor}">${escapeHtml(s.entry_type)}</span></div>
                            ${entryWebhookHtml}
                        </div>
                    </div>
                </div>

                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header"><i class="bi bi-file-earmark-text"></i> Контракты</div>
                        <div class="card-body">
                            ${contractsHtml}
                        </div>
                    </div>
                </div>

                <!-- StopLoss -->
                <div class="col-md-6">
                    ${slHtml}
                </div>

                <!-- TakeProfit -->
                <div class="col-md-6">
                    ${tpHtml}
                </div>

                <!-- Действия -->
                <div class="col-12">
                    <div class="d-flex gap-2">
                        <a href="/strategies/${s.id}/edit" class="btn btn-outline-primary btn-sm">
                            <i class="bi bi-pencil"></i> Редактировать
                        </a>
                        <button class="btn btn-outline-${s.is_active ? 'secondary' : 'success'} btn-sm" onclick="toggleStrategyStatus('${s.id}')">
                            <i class="bi bi-${s.is_active ? 'pause' : 'play'}-circle"></i> ${s.is_active ? 'Деактивировать' : 'Активировать'}
                        </button>
                        <button class="btn btn-outline-danger btn-sm" onclick="confirmDelete('${s.id}', '${escapeHtml(s.name)}')">
                            <i class="bi bi-trash"></i> Удалить
                        </button>
                    </div>
                </div>
            </div>
        `;

        div.innerHTML = html;

    } catch (e) {
        div.innerHTML = `<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Ошибка загрузки: ${escapeHtml(e.message)}</div>`;
    }
}

function renderTriggerInfo(title, config, icon, color) {
    if (!config || !config.enabled) {
        return `
            <div class="card">
                <div class="card-header"><i class="bi ${icon}"></i> ${title}</div>
                <div class="card-body"><span class="text-muted">Не настроен</span></div>
            </div>
        `;
    }

    let innerHtml = '';
    if (config.trigger_type === 'conditions') {
        const cond = config.conditions || {};
        innerHtml = `
            <div><i class="bi bi-sliders"></i> По условиям:</div>
            ${cond.price != null ? `<div class="ms-3">Цена: <strong>${cond.price}</strong></div>` : ''}
            ${cond.percent != null ? `<div class="ms-3">Процент: <strong>${cond.percent}%</strong></div>` : ''}
            ${!cond.price && !cond.percent ? '<div class="ms-3 text-muted">Параметры не заданы</div>' : ''}
        `;
    } else {
        const wh = config.webhook || {};
        innerHtml = `
            <div><i class="bi bi-webhook"></i> Webhook: <strong>${escapeHtml(wh.name || '—')}</strong></div>
        `;
    }

    return `
        <div class="card">
            <div class="card-header"><i class="bi ${icon}"></i> ${title} <span class="badge bg-${color} ms-2">${config.trigger_type === 'conditions' ? 'Условия' : 'Webhook'}</span></div>
            <div class="card-body">${innerHtml}</div>
        </div>
    `;
}

// ─── Инициализация формы ────────────────────────────────────────────

async function initStrategyForm(mode, strategyId) {
    // Привязка динамики полей
    bindFormDynamics();

    if (mode === 'edit' && strategyId) {
        await loadStrategyForEdit(strategyId);
    }

    // Привязка отправки формы
    const form = document.getElementById('strategy-form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await saveStrategy(mode, strategyId);
        });
    }
}

async function loadStrategyForEdit(strategyId) {
    try {
        const res = await fetch(`/api/strategies/${strategyId}`);
        const data = await res.json();

        if (!data.success) {
            showToast('Ошибка', data.error, 'danger');
            return;
        }

        const s = data.data;

        // Основная информация
        const nameEl = document.getElementById('strategy-name');
        if (nameEl) nameEl.value = s.name || '';

        const descEl = document.getElementById('strategy-desc');
        if (descEl) descEl.value = s.description || '';

        const activeEl = document.getElementById('strategy-active');
        if (activeEl) activeEl.checked = s.is_active !== false;

        // Актив
        const assetType = s.asset_type || 'BTC';
        if (assetType === 'BTC') document.getElementById('asset-btc').checked = true;
        else if (assetType === 'ETH') document.getElementById('asset-eth').checked = true;
        else {
            document.getElementById('asset-other').checked = true;
            document.getElementById('custom-asset').style.display = '';
        }
        const customAssetEl = document.getElementById('custom-asset');
        if (customAssetEl) customAssetEl.value = s.custom_asset || '';

        // Объём
        const volumeEl = document.getElementById('volume');
        if (volumeEl) volumeEl.value = s.volume || 0;

        const volCurEl = document.getElementById('volume-currency');
        if (volCurEl) volCurEl.value = s.volume_currency || 'USDT';

        const splitEl = document.getElementById('volume-split');
        if (splitEl) splitEl.checked = s.volume_split || false;

        const splitCountEl = document.getElementById('split-count');
        if (splitCountEl) splitCountEl.value = s.split_count || 1;

        document.getElementById('split-count-group').style.display = splitEl && splitEl.checked ? '' : 'none';

        // Контракты
        if (s.contracts && s.contracts.length > 0) {
            for (const c of s.contracts) {
                const periodId = c.period; // daily, weekly, monthly
                const posId = c.position;  // nearest, middle, farthest

                // Включаем период
                const periodCheck = document.getElementById(`contract-${periodId}`);
                if (periodCheck) {
                    periodCheck.checked = true;
                    const posDiv = document.getElementById(`${periodId}-positions`);
                    if (posDiv) posDiv.style.display = '';
                }

                // Включаем позицию
                const posCheck = document.getElementById(`${periodId}-${posId}`);
                if (posCheck) posCheck.checked = true;
            }
        }

        // Тип входа
        const entryType = s.entry_type || 'Call';
        if (entryType === 'Call') document.getElementById('entry-call').checked = true;
        else if (entryType === 'Put') document.getElementById('entry-put').checked = true;
        else document.getElementById('entry-call-put').checked = true;

        // Webhook входа
        const entryWh = s.entry_webhook || {};
        const entryWhEnabled = document.getElementById('entry-webhook-enabled');
        if (entryWhEnabled) entryWhEnabled.checked = entryWh.enabled || false;
        document.getElementById('entry-webhook-fields').style.display = entryWhEnabled && entryWhEnabled.checked ? '' : 'none';
        const entryWhName = document.getElementById('entry-webhook-name');
        if (entryWhName) entryWhName.value = entryWh.name || '';

        // StopLoss
        const sl = s.stop_loss || {};
        const slEnabled = document.getElementById('sl-enabled');
        if (slEnabled) slEnabled.checked = sl.enabled || false;
        document.getElementById('sl-fields').style.display = slEnabled && slEnabled.checked ? '' : 'none';

        if (sl.trigger_type === 'webhook') {
            document.getElementById('sl-trigger-webhook').checked = true;
            document.getElementById('sl-conditions-fields').style.display = 'none';
            document.getElementById('sl-webhook-fields').style.display = '';
        } else {
            document.getElementById('sl-trigger-conditions').checked = true;
            document.getElementById('sl-conditions-fields').style.display = '';
            document.getElementById('sl-webhook-fields').style.display = 'none';
        }
        const slCond = sl.conditions || {};
        const slPrice = document.getElementById('sl-price');
        if (slPrice) slPrice.value = slCond.price || '';
        const slPercent = document.getElementById('sl-percent');
        if (slPercent) slPercent.value = slCond.percent || '';
        const slWhName = document.getElementById('sl-webhook-name');
        if (slWhName) slWhName.value = (sl.webhook && sl.webhook.name) || '';

        // TakeProfit
        const tp = s.take_profit || {};
        const tpEnabled = document.getElementById('tp-enabled');
        if (tpEnabled) tpEnabled.checked = tp.enabled || false;
        document.getElementById('tp-fields').style.display = tpEnabled && tpEnabled.checked ? '' : 'none';

        if (tp.trigger_type === 'webhook') {
            document.getElementById('tp-trigger-webhook').checked = true;
            document.getElementById('tp-conditions-fields').style.display = 'none';
            document.getElementById('tp-webhook-fields').style.display = '';
        } else {
            document.getElementById('tp-trigger-conditions').checked = true;
            document.getElementById('tp-conditions-fields').style.display = '';
            document.getElementById('tp-webhook-fields').style.display = 'none';
        }
        const tpCond = tp.conditions || {};
        const tpPrice = document.getElementById('tp-price');
        if (tpPrice) tpPrice.value = tpCond.price || '';
        const tpPercent = document.getElementById('tp-percent');
        if (tpPercent) tpPercent.value = tpCond.percent || '';
        const tpWhName = document.getElementById('tp-webhook-name');
        if (tpWhName) tpWhName.value = (tp.webhook && tp.webhook.name) || '';

    } catch (e) {
        showToast('Ошибка', `Не удалось загрузить стратегию: ${e.message}`, 'danger');
    }
}

// ─── Динамика формы ─────────────────────────────────────────────────

function bindFormDynamics() {
    // Other актив -> показать поле тикера
    document.querySelectorAll('input[name="asset"]').forEach(radio => {
        radio.addEventListener('change', () => {
            const isOther = document.getElementById('asset-other').checked;
            document.getElementById('custom-asset').style.display = isOther ? '' : 'none';
        });
    });

    // Разделить объём -> показать количество контрактов
    const volumeSplit = document.getElementById('volume-split');
    if (volumeSplit) {
        volumeSplit.addEventListener('change', () => {
            document.getElementById('split-count-group').style.display = volumeSplit.checked ? '' : 'none';
        });
    }

    // Контракты — переключение периодов
    ['daily', 'weekly', 'monthly'].forEach(period => {
        const check = document.getElementById(`contract-${period}`);
        if (check) {
            check.addEventListener('change', () => {
                document.getElementById(`${period}-positions`).style.display = check.checked ? '' : 'none';
                // Сбросить позиции при выключении
                if (!check.checked) {
                    document.querySelectorAll(`#${period}-positions input[type="checkbox"]`).forEach(cb => cb.checked = false);
                }
            });
        }
    });

    // Webhook входа
    const entryWhEnabled = document.getElementById('entry-webhook-enabled');
    if (entryWhEnabled) {
        entryWhEnabled.addEventListener('change', () => {
            document.getElementById('entry-webhook-fields').style.display = entryWhEnabled.checked ? '' : 'none';
        });
    }

    // StopLoss
    const slEnabled = document.getElementById('sl-enabled');
    if (slEnabled) {
        slEnabled.addEventListener('change', () => {
            document.getElementById('sl-fields').style.display = slEnabled.checked ? '' : 'none';
        });
    }
    document.querySelectorAll('input[name="sl-trigger"]').forEach(radio => {
        radio.addEventListener('change', () => {
            const isWebhook = document.getElementById('sl-trigger-webhook').checked;
            document.getElementById('sl-conditions-fields').style.display = isWebhook ? 'none' : '';
            document.getElementById('sl-webhook-fields').style.display = isWebhook ? '' : 'none';
        });
    });

    // TakeProfit
    const tpEnabled = document.getElementById('tp-enabled');
    if (tpEnabled) {
        tpEnabled.addEventListener('change', () => {
            document.getElementById('tp-fields').style.display = tpEnabled.checked ? '' : 'none';
        });
    }
    document.querySelectorAll('input[name="tp-trigger"]').forEach(radio => {
        radio.addEventListener('change', () => {
            const isWebhook = document.getElementById('tp-trigger-webhook').checked;
            document.getElementById('tp-conditions-fields').style.display = isWebhook ? 'none' : '';
            document.getElementById('tp-webhook-fields').style.display = isWebhook ? '' : 'none';
        });
    });
}

// ─── Сохранение стратегии ───────────────────────────────────────────

async function saveStrategy(mode, strategyId) {
    const name = document.getElementById('strategy-name').value.trim();
    if (!name) {
        showToast('Ошибка', 'Введите название стратегии', 'danger');
        return;
    }

    // Собираем данные
    const assetType = document.querySelector('input[name="asset"]:checked').value;
    const customAsset = document.getElementById('custom-asset').value.trim();

    const volume = parseFloat(document.getElementById('volume').value) || 0;
    const volumeCurrency = document.getElementById('volume-currency').value;
    const volumeSplit = document.getElementById('volume-split').checked;
    const splitCount = parseInt(document.getElementById('split-count').value) || 1;

    // Контракты
    const contracts = [];
    ['daily', 'weekly', 'monthly'].forEach(period => {
        const periodCheck = document.getElementById(`contract-${period}`);
        if (periodCheck && periodCheck.checked) {
            ['nearest', 'middle', 'farthest'].forEach(pos => {
                const posCheck = document.getElementById(`${period}-${pos}`);
                if (posCheck && posCheck.checked) {
                    contracts.push({ period, position: pos });
                }
            });
        }
    });

    const entryType = document.querySelector('input[name="entry-type"]:checked').value;

    // Webhook входа
    const entryWebhookEnabled = document.getElementById('entry-webhook-enabled').checked;
    const entryWebhookName = document.getElementById('entry-webhook-name').value.trim();

    // StopLoss
    const slEnabled = document.getElementById('sl-enabled').checked;
    const slTriggerType = document.querySelector('input[name="sl-trigger"]:checked').value;
    const slPrice = document.getElementById('sl-price').value ? parseFloat(document.getElementById('sl-price').value) : null;
    const slPercent = document.getElementById('sl-percent').value ? parseFloat(document.getElementById('sl-percent').value) : null;
    const slWebhookName = document.getElementById('sl-webhook-name').value.trim();

    // TakeProfit
    const tpEnabled = document.getElementById('tp-enabled').checked;
    const tpTriggerType = document.querySelector('input[name="tp-trigger"]:checked').value;
    const tpPrice = document.getElementById('tp-price').value ? parseFloat(document.getElementById('tp-price').value) : null;
    const tpPercent = document.getElementById('tp-percent').value ? parseFloat(document.getElementById('tp-percent').value) : null;
    const tpWebhookName = document.getElementById('tp-webhook-name').value.trim();

    const isActive = document.getElementById('strategy-active').checked;
    const description = document.getElementById('strategy-desc').value.trim();

    const body = {
        name,
        description,
        asset_type: assetType,
        custom_asset: assetType === 'Other' ? customAsset : '',
        volume,
        volume_currency: volumeCurrency,
        volume_split: volumeSplit,
        split_count: splitCount,
        contracts,
        entry_type: entryType,
        entry_webhook: { enabled: entryWebhookEnabled, name: entryWebhookName },
        stop_loss: {
            enabled: slEnabled,
            trigger_type: slTriggerType,
            conditions: slEnabled && slTriggerType === 'conditions' ? { enabled: true, price: slPrice, percent: slPercent } : null,
            webhook: slEnabled && slTriggerType === 'webhook' ? { enabled: true, name: slWebhookName } : null,
        },
        take_profit: {
            enabled: tpEnabled,
            trigger_type: tpTriggerType,
            conditions: tpEnabled && tpTriggerType === 'conditions' ? { enabled: true, price: tpPrice, percent: tpPercent } : null,
            webhook: tpEnabled && tpTriggerType === 'webhook' ? { enabled: true, name: tpWebhookName } : null,
        },
        is_active: isActive,
    };

    const saveBtn = document.getElementById('save-btn');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Сохранение...';
    }

    try {
        let url, method;
        if (mode === 'create') {
            url = '/api/strategies';
            method = 'POST';
        } else {
            url = `/api/strategies/${strategyId}`;
            method = 'PUT';
        }

        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        const data = await res.json();

        if (data.success) {
            showToast('Успех', mode === 'create' ? 'Стратегия создана' : 'Стратегия обновлена', 'success');
            setTimeout(() => {
                window.location.href = `/strategies/${data.data.id}`;
            }, 500);
        } else {
            showToast('Ошибка', data.error, 'danger');
        }
    } catch (e) {
        showToast('Ошибка', e.message, 'danger');
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = `<i class="bi bi-check-lg"></i> ${mode === 'create' ? 'Создать' : 'Сохранить'}`;
        }
    }
}

// ─── Удаление стратегии ─────────────────────────────────────────────

function confirmDelete(strategyId, strategyName) {
    deleteTargetId = strategyId;
    const nameEl = document.getElementById('delete-strategy-name');
    if (nameEl) nameEl.textContent = strategyName;

    const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
    modal.show();
}

document.addEventListener('DOMContentLoaded', () => {
    const confirmBtn = document.getElementById('confirm-delete-btn');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', async () => {
            if (!deleteTargetId) return;

            try {
                const res = await fetch(`/api/strategies/${deleteTargetId}`, { method: 'DELETE' });
                const data = await res.json();

                if (data.success) {
                    showToast('Удалено', 'Стратегия удалена', 'success');
                    bootstrap.Modal.getInstance(document.getElementById('deleteModal')).hide();
                    setTimeout(() => {
                        window.location.href = '/strategies';
                    }, 500);
                } else {
                    showToast('Ошибка', data.error, 'danger');
                }
            } catch (e) {
                showToast('Ошибка', e.message, 'danger');
            }
        });
    }
});

// ─── Переключение статуса стратегии ─────────────────────────────────

async function toggleStrategyStatus(strategyId) {
    try {
        const res = await fetch(`/api/strategies/${strategyId}/toggle`, { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            showToast('Статус изменён', data.message, 'success');
            // Перезагружаем детальную информацию
            loadStrategyDetail(strategyId);
        } else {
            showToast('Ошибка', data.error, 'danger');
        }
    } catch (e) {
        showToast('Ошибка', e.message, 'danger');
    }
}
