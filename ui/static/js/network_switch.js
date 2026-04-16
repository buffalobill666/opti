/**
 * Переключение сети со страницы API Keys (свитч в карточке биржи).
 * Для Bybit: testnet switch = demo режим
 * Функции updateNetworkBadge и toggleNetwork — в main.js.
 */

async function switchNetwork(exchange, testnet) {
    // Для Bybit: переключатель testnet = demo режим
    const isBybitDemo = exchange === 'bybit' && testnet;

    try {
        const response = await fetch('/api/keys/network', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ exchange, testnet: isBybitDemo }),
        });

        const result = await response.json();

        if (result.success) {
            // Обновляем бейдж в навбаре (единый для всех страниц)
            updateNetworkBadge(exchange, testnet);
            // Обновляем URL
            loadNetworkUrl(exchange);
            showToast(
                'Сеть изменена',
                `${exchange.toUpperCase()} переключён на ${isBybitDemo ? 'demo' : (testnet ? 'testnet' : 'mainnet')}`,
                'success'
            );
            // Перезагружаем страницу чтобы данные обновились из нового .env
            setTimeout(() => {
                window.location.reload();
            }, 500);
        } else {
            showToast('Ошибка', result.error, 'danger');
            // Восстанавливаем положение свитча
            const checkbox = document.getElementById(`${exchange}-testnet-switch`);
            if (checkbox) checkbox.checked = !testnet;
        }
    } catch (error) {
        showToast('Ошибка', error.message, 'danger');
        const checkbox = document.getElementById(`${exchange}-testnet-switch`);
        if (checkbox) checkbox.checked = !testnet;
    }
}
