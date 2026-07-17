function chartColors() {
    return {
        text: 'rgba(235, 242, 255, .82)',
        muted: 'rgba(152, 166, 199, .82)',
        grid: 'rgba(255, 255, 255, .08)',
        zero: 'rgba(255, 255, 255, .18)',
        green: '#35f28d',
        red: '#ff5268',
        purple: '#9a78ff',
        blue: '#58aaff',
        cyan: '#20e7df',
        gray: '#7b8aa8'
    };
}

function localDateTime() {
    const now = new Date();
    const pad = value => String(value).padStart(2, '0');
    return {
        date: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`,
        time: `${pad(now.getHours())}:${pad(now.getMinutes())}`
    };
}

function fillCurrentTradeDateTime(force = false) {
    const dateInput = document.getElementById('trade-date');
    const timeInput = document.getElementById('trade-time');
    if (!dateInput || !timeInput) return;

    const current = localDateTime();
    if (force || !dateInput.value) {
        dateInput.value = current.date;
        dateInput.dataset.automatic = 'true';
    }
    if (force || !timeInput.value) {
        timeInput.value = current.time;
        timeInput.dataset.automatic = 'true';
    }
}

function initAutomaticDateTime() {
    const dateInput = document.getElementById('trade-date');
    const timeInput = document.getElementById('trade-time');
    const form = document.querySelector('[data-new-trade-form]');
    if (!dateInput || !timeInput) return;

    dateInput.dataset.automatic = 'true';
    timeInput.dataset.automatic = 'true';
    fillCurrentTradeDateTime(false);

    [dateInput, timeInput].forEach(input => {
        input.addEventListener('input', () => {
            input.dataset.automatic = 'false';
        });
    });

    document.querySelectorAll('[data-add-trade]').forEach(link => {
        link.addEventListener('click', () => fillCurrentTradeDateTime(true));
    });

    if (form) {
        form.addEventListener('submit', () => {
            const current = localDateTime();
            if (dateInput.dataset.automatic === 'true') dateInput.value = current.date;
            if (timeInput.dataset.automatic === 'true') timeInput.value = current.time;
        });
    }
}

function formatMoney(value, currency, compact = false) {
    const number = Number(value) || 0;
    try {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency,
            notation: compact ? 'compact' : 'standard',
            minimumFractionDigits: compact ? 0 : 2,
            maximumFractionDigits: compact ? 1 : 2
        }).format(number);
    } catch (error) {
        return `${number.toLocaleString('en-US', { maximumFractionDigits: 2 })} ${currency}`;
    }
}

function formatTradeDate(dateValue, timeValue = '') {
    const parts = String(dateValue).split('-').map(Number);
    if (parts.length !== 3 || parts.some(Number.isNaN)) return `${dateValue} ${timeValue}`.trim();
    const date = new Date(parts[0], parts[1] - 1, parts[2]);
    const formatted = new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    }).format(date);
    return timeValue ? `${formatted} at ${timeValue}` : formatted;
}

function formatMonth(value) {
    const [year, month] = String(value).split('-').map(Number);
    if (!year || !month) return value;
    return new Intl.DateTimeFormat('en-US', { month: 'short', year: 'numeric' })
        .format(new Date(year, month - 1, 1));
}

const emptyStatePlugin = {
    id: 'emptyState',
    afterDraw(chart, args, options) {
        const hasPoints = chart.data.datasets.some(dataset => Array.isArray(dataset.data) && dataset.data.length > 0);
        if (hasPoints) return;

        const { ctx, chartArea } = chart;
        if (!chartArea) return;
        ctx.save();
        ctx.fillStyle = chartColors().muted;
        ctx.font = '600 14px Inter, Segoe UI, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(options.message || 'No data yet', (chartArea.left + chartArea.right) / 2, (chartArea.top + chartArea.bottom) / 2);
        ctx.restore();
    }
};

const doughnutCenterText = {
    id: 'doughnutCenterText',
    afterDraw(chart, args, options) {
        const { ctx, chartArea } = chart;
        if (!chartArea) return;
        const centerX = (chartArea.left + chartArea.right) / 2;
        const centerY = (chartArea.top + chartArea.bottom) / 2;

        ctx.save();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#eef4ff';
        ctx.font = '800 28px Inter, Segoe UI, sans-serif';
        ctx.fillText(options.value || '0', centerX, centerY - 7);
        ctx.fillStyle = chartColors().muted;
        ctx.font = '600 11px Inter, Segoe UI, sans-serif';
        ctx.fillText(options.label || 'TRADES', centerX, centerY + 18);
        ctx.restore();
    }
};

function commonPlugins() {
    const c = chartColors();
    return {
        legend: {
            position: 'top',
            align: 'end',
            labels: {
                color: c.text,
                usePointStyle: true,
                pointStyle: 'circle',
                boxWidth: 8,
                boxHeight: 8,
                padding: 18,
                font: { size: 12, weight: '600' }
            }
        },
        tooltip: {
            backgroundColor: 'rgba(5, 7, 22, .96)',
            titleColor: '#eef4ff',
            bodyColor: c.text,
            borderColor: 'rgba(255, 255, 255, .14)',
            borderWidth: 1,
            padding: 12,
            cornerRadius: 10,
            displayColors: true
        }
    };
}

async function initCharts() {
    const equityCanvas = document.getElementById('equityChart');
    if (!equityCanvas || typeof Chart === 'undefined') return;

    try {
        const response = await fetch('/api/charts');
        if (!response.ok) throw new Error('Chart data could not be loaded.');
        const data = await response.json();
        const c = chartColors();
        const currency = data.currency || 'USD';

        Chart.defaults.color = c.text;
        Chart.defaults.font.family = 'Inter, Segoe UI, Arial, sans-serif';
        Chart.defaults.animation.duration = 450;

        const equityLabels = ['Start', ...data.equity.map(point => `#${point.number}`)];
        const equityValues = [data.start_balance, ...data.equity.map(point => point.value)];
        const pointColors = [c.gray, ...data.equity.map(point => point.result === 'LOSS' ? c.red : point.result === 'WIN' ? c.green : c.gray)];
        const equityDatasets = [{
            label: 'Account balance',
            data: equityValues,
            borderColor: c.green,
            backgroundColor: 'rgba(53, 242, 141, .10)',
            fill: {
                target: { value: data.start_balance },
                above: 'rgba(53, 242, 141, .13)',
                below: 'rgba(255, 82, 104, .11)'
            },
            cubicInterpolationMode: 'monotone',
            tension: .18,
            borderWidth: 3,
            pointRadius: equityValues.length > 45 ? 0 : 3,
            pointHoverRadius: 7,
            pointBackgroundColor: pointColors,
            pointBorderColor: '#0b1125',
            pointBorderWidth: 2,
            segment: {
                borderColor: context => context.p1.parsed.y >= data.start_balance ? c.green : c.red
            }
        }];

        if (equityValues.length > 1) {
            equityDatasets.push({
                label: 'Starting balance',
                data: equityValues.map(() => data.start_balance),
                borderColor: 'rgba(152, 166, 199, .65)',
                borderDash: [6, 6],
                borderWidth: 1.5,
                pointRadius: 0,
                pointHoverRadius: 0,
                fill: false
            });
        }

        const equityPlugins = commonPlugins();
        equityPlugins.tooltip.callbacks = {
            title(items) {
                const index = items[0].dataIndex;
                if (index === 0) return 'Starting balance';
                const point = data.equity[index - 1];
                return `${formatTradeDate(point.date, point.time)} • ${point.instrument}`;
            },
            label(context) {
                const label = context.datasetIndex === 1 ? 'Starting balance' : 'Balance';
                return `${label}: ${formatMoney(context.parsed.y, currency)}`;
            },
            afterLabel(context) {
                if (context.datasetIndex !== 0 || context.dataIndex === 0) return '';
                const point = data.equity[context.dataIndex - 1];
                const sign = point.pnl > 0 ? '+' : '';
                return `Trade P/L: ${sign}${formatMoney(point.pnl, currency)} • ${point.direction}`;
            }
        };

        new Chart(equityCanvas, {
            type: 'line',
            data: { labels: equityLabels, datasets: equityDatasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                layout: { padding: { top: 4, right: 8 } },
                plugins: equityPlugins,
                scales: {
                    x: {
                        grid: { display: false },
                        border: { color: c.zero },
                        ticks: {
                            color: c.muted,
                            autoSkip: true,
                            maxTicksLimit: window.innerWidth < 700 ? 6 : 12,
                            maxRotation: 0,
                            font: { size: 11 }
                        },
                        title: { display: true, text: 'Trade number', color: c.muted, padding: { top: 8 } }
                    },
                    y: {
                        grace: '8%',
                        grid: { color: c.grid },
                        border: { display: false },
                        ticks: {
                            color: c.muted,
                            maxTicksLimit: 7,
                            callback: value => formatMoney(value, currency, false)
                        }
                    }
                }
            }
        });

        const resultValues = [data.result.WIN, data.result.LOSS, data.result.BE];
        const resultTotal = resultValues.reduce((sum, value) => sum + value, 0);
        const resultPlugins = commonPlugins();
        resultPlugins.legend.position = 'bottom';
        resultPlugins.legend.align = 'center';
        resultPlugins.tooltip.callbacks = {
            label(context) {
                const value = context.raw || 0;
                const percent = resultTotal ? (value / resultTotal * 100).toFixed(1) : '0.0';
                return `${context.label}: ${value} (${percent}%)`;
            }
        };
        resultPlugins.doughnutCenterText = { value: String(resultTotal), label: resultTotal === 1 ? 'TRADE' : 'TRADES' };

        new Chart(document.getElementById('resultChart'), {
            type: 'doughnut',
            data: {
                labels: ['Wins', 'Losses', 'Break-even'],
                datasets: [{
                    data: resultValues,
                    backgroundColor: [c.green, c.red, c.gray],
                    borderColor: '#0d142c',
                    borderWidth: 4,
                    hoverOffset: 5
                }]
            },
            plugins: [doughnutCenterText],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                layout: { padding: 8 },
                plugins: resultPlugins
            }
        });

        const monthlyPlugins = commonPlugins();
        monthlyPlugins.legend.display = false;
        monthlyPlugins.tooltip.callbacks = {
            label: context => `Net P/L: ${formatMoney(context.parsed.y, currency)}`
        };

        new Chart(document.getElementById('monthlyChart'), {
            type: 'bar',
            data: {
                labels: data.monthly.map(point => formatMonth(point.label)),
                datasets: [{
                    label: 'Net P/L',
                    data: data.monthly.map(point => point.value),
                    backgroundColor: data.monthly.map(point => point.value >= 0 ? 'rgba(53, 242, 141, .82)' : 'rgba(255, 82, 104, .82)'),
                    borderColor: data.monthly.map(point => point.value >= 0 ? c.green : c.red),
                    borderWidth: 1,
                    borderRadius: 7,
                    borderSkipped: false,
                    maxBarThickness: 56
                }]
            },
            plugins: [emptyStatePlugin],
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: { ...monthlyPlugins, emptyState: { message: 'Add a trade to see monthly P/L' } },
                scales: {
                    x: {
                        grid: { display: false },
                        border: { color: c.zero },
                        ticks: { color: c.muted, maxRotation: 0, autoSkip: true, maxTicksLimit: 6 }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: context => context.tick.value === 0 ? c.zero : c.grid },
                        border: { display: false },
                        ticks: { color: c.muted, maxTicksLimit: 6, callback: value => formatMoney(value, currency, true) }
                    }
                }
            }
        });

        const sessionPlugins = commonPlugins();
        sessionPlugins.legend.display = false;
        sessionPlugins.tooltip.callbacks = {
            label: context => `Net P/L: ${formatMoney(context.parsed.x, currency)}`
        };

        new Chart(document.getElementById('sessionChart'), {
            type: 'bar',
            data: {
                labels: data.session.map(point => point.label),
                datasets: [{
                    label: 'Net P/L',
                    data: data.session.map(point => point.value),
                    backgroundColor: data.session.map(point => point.value >= 0 ? 'rgba(88, 170, 255, .82)' : 'rgba(255, 82, 104, .82)'),
                    borderColor: data.session.map(point => point.value >= 0 ? c.blue : c.red),
                    borderWidth: 1,
                    borderRadius: 7,
                    borderSkipped: false,
                    maxBarThickness: 34
                }]
            },
            plugins: [emptyStatePlugin],
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: { ...sessionPlugins, emptyState: { message: 'Add a trade to compare sessions' } },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: { color: context => context.tick.value === 0 ? c.zero : c.grid },
                        border: { display: false },
                        ticks: { color: c.muted, maxTicksLimit: 5, callback: value => formatMoney(value, currency, true) }
                    },
                    y: {
                        grid: { display: false },
                        border: { color: c.zero },
                        ticks: { color: c.text, font: { weight: '600' } }
                    }
                }
            }
        });
    } catch (error) {
        const panel = equityCanvas.closest('.chart-panel');
        if (panel) {
            const message = document.createElement('p');
            message.className = 'chart-error';
            message.textContent = error.message;
            panel.appendChild(message);
        }
    }
}

function openImageModal(src) {
    const modal = document.getElementById('imageModal');
    const image = document.getElementById('modalImage');
    if (!modal || !image) return;
    image.src = src;
    modal.classList.add('show');
}

function closeImageModal() {
    const modal = document.getElementById('imageModal');
    if (modal) modal.classList.remove('show');
}

document.addEventListener('keydown', event => {
    if (event.key === 'Escape') closeImageModal();
});

document.addEventListener('DOMContentLoaded', () => {
    initAutomaticDateTime();
    initCharts();
});
