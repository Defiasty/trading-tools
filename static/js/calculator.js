const CONTRACTS = {
    NQ: { point: 20, tick: 0.25 }, MNQ: { point: 2, tick: 0.25 },
    ES: { point: 50, tick: 0.25 }, MES: { point: 5, tick: 0.25 },
    YM: { point: 5, tick: 1 }, MYM: { point: 0.5, tick: 1 },
    RTY: { point: 50, tick: 0.1 }, M2K: { point: 5, tick: 0.1 },
    CL: { point: 1000, tick: 0.01 }, MCL: { point: 100, tick: 0.01 },
    GC: { point: 100, tick: 0.1 }, MGC: { point: 10, tick: 0.1 }
};

const byId = id => document.getElementById(id);
const root = document.querySelector('[data-position-calculator]');

if (root) {
    let lastPlan = null;
    const currency = root.dataset.currency || 'USD';
    const fields = ['calcInstrument', 'calcAccount', 'calcRisk', 'calcRiskMode', 'calcStopMode', 'calcStopPoints', 'calcEntry', 'calcStop', 'calcDirection', 'calcRr', 'calcCommission'];
    const inputs = Object.fromEntries(fields.map(id => [id, byId(id)]));
    const number = value => Number(value || 0);
    const roundToTick = (value, tick) => Math.round(value / tick) * tick;
    const decimals = tick => String(tick).includes('.') ? String(tick).split('.')[1].length : 0;
    const money = value => {
        try { return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 2 }).format(value || 0); }
        catch (_) { return `${number(value).toFixed(2)} ${currency}`; }
    };

    function values() {
        const account = number(inputs.calcAccount.value);
        const riskInput = number(inputs.calcRisk.value);
        const riskBudget = inputs.calcRiskMode.value === 'percent' ? account * riskInput / 100 : riskInput;
        const priceMode = inputs.calcStopMode.value === 'prices';
        const entry = number(inputs.calcEntry.value);
        const stop = number(inputs.calcStop.value);
        const stopPoints = priceMode ? Math.abs(entry - stop) : number(inputs.calcStopPoints.value);
        return { symbol: inputs.calcInstrument.value, account, riskInput, riskBudget, priceMode, entry, stop, stopPoints, direction: inputs.calcDirection.value, rr: number(inputs.calcRr.value), commission: number(inputs.calcCommission.value) };
    }

    function validate(v) {
        if (v.account <= 0) return 'Account size must be greater than zero.';
        if (v.riskBudget <= 0) return 'Risk limit must be greater than zero.';
        if (v.priceMode && (v.entry <= 0 || v.stop <= 0)) return 'Enter a valid entry and stop price.';
        if (v.stopPoints <= 0) return 'Stop distance must be greater than zero.';
        if (v.rr <= 0) return 'Reward/risk must be greater than zero.';
        if (v.commission < 0) return 'Commission cannot be negative.';
        return '';
    }

    function calculate(save = false) {
        const v = values();
        const error = validate(v);
        byId('calcError').textContent = error;
        byId('calcError').classList.toggle('hidden', !error);
        if (error) return;

        const spec = CONTRACTS[v.symbol];
        const riskOne = v.stopPoints * spec.point + v.commission;
        const contracts = Math.max(0, Math.floor(v.riskBudget / riskOne));
        const actualRisk = contracts * riskOne;
        const unused = Math.max(0, v.riskBudget - actualRisk);
        const grossRewardOne = v.stopPoints * v.rr * spec.point;
        const potentialProfit = contracts * Math.max(0, grossRewardOne - v.commission);
        const targetPoints = v.stopPoints * v.rr;
        const targetPrice = roundToTick(v.direction === 'long' ? v.entry + targetPoints : v.entry - targetPoints, spec.tick);
        lastPlan = { instrument: v.symbol, contracts, direction: v.direction === 'long' ? 'Buy' : 'Sell', entry_price: v.priceMode ? v.entry : '', stop_loss: v.priceMode ? v.stop : '', take_profit: v.priceMode ? targetPrice : '', commission: v.commission };

        byId('calcResultSymbol').textContent = v.symbol;
        byId('calcContracts').textContent = contracts;
        byId('calcContractsLabel').textContent = contracts === 1 ? 'contract' : 'contracts';
        byId('calcBudget').textContent = money(v.riskBudget);
        byId('calcRiskOne').textContent = money(riskOne);
        byId('calcActualRisk').textContent = money(actualRisk);
        byId('calcActualPercent').textContent = `${(actualRisk / v.account * 100).toFixed(2)}%`;
        byId('calcProfit').textContent = money(potentialProfit);
        byId('calcUnused').textContent = money(unused);
        byId('calcPlanStop').textContent = `${v.stopPoints.toFixed(2)} pts`;
        byId('calcTick').textContent = `${spec.tick} / ${money(spec.tick * spec.point)}`;
        byId('calcTargetPoints').textContent = `${targetPoints.toFixed(2)} pts`;
        byId('calcTargetRow').classList.toggle('hidden', !v.priceMode);
        byId('calcTargetPrice').textContent = targetPrice.toFixed(decimals(spec.tick));

        let warning = '';
        if (contracts < 1) warning = `One ${v.symbol} contract risks ${money(riskOne)}, which exceeds your ${money(v.riskBudget)} limit. Use a tighter stop, a higher limit, or a Micro contract.`;
        else if (inputs.calcRiskMode.value === 'percent' && v.riskInput > 2) warning = 'Risk is above 2% of the account. Confirm that this matches your trading plan and evaluation rules.';
        byId('calcWarning').textContent = warning;
        byId('calcWarning').classList.toggle('hidden', !warning);

        if (save) saveHistory({ ...v, riskOne, contracts, actualRisk, potentialProfit, time: new Date().toISOString() });
    }

    function history() {
        try { return JSON.parse(localStorage.getItem('tracker_position_history') || '[]'); }
        catch (_) { return []; }
    }

    function saveHistory(row) {
        const rows = [row, ...history()].slice(0, 20);
        localStorage.setItem('tracker_position_history', JSON.stringify(rows));
        renderHistory();
    }

    function renderHistory() {
        const rows = history();
        const body = byId('calcHistoryBody');
        body.textContent = '';
        byId('calcEmptyHistory').classList.toggle('hidden', rows.length > 0);
        rows.forEach(row => {
            const tr = document.createElement('tr');
            const cells = [new Date(row.time).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }), row.symbol, money(row.account), `${number(row.stopPoints).toFixed(2)} pts`, money(row.riskBudget), row.contracts, money(row.actualRisk), money(row.potentialProfit)];
            cells.forEach((value, index) => { const td = document.createElement('td'); td.textContent = value; if (index === 1 || index === 5) td.className = 'history-emphasis'; tr.appendChild(td); });
            body.appendChild(tr);
        });
    }

    function updateStopMode() {
        const priceMode = inputs.calcStopMode.value === 'prices';
        byId('calcPointsWrap').classList.toggle('hidden', priceMode);
        byId('calcEntryWrap').classList.toggle('hidden', !priceMode);
        byId('calcStopWrap').classList.toggle('hidden', !priceMode);
        calculate();
    }

    fields.forEach(id => inputs[id].addEventListener('input', calculate));
    inputs.calcStopMode.addEventListener('change', updateStopMode);
    byId('calcSave').addEventListener('click', () => calculate(true));
    byId('calcClear').addEventListener('click', () => { localStorage.removeItem('tracker_position_history'); renderHistory(); });
    byId('calcUsePlan').addEventListener('click', () => {
        calculate();
        if (!lastPlan || lastPlan.contracts < 1) return;
        sessionStorage.setItem('tracker_trade_plan', JSON.stringify(lastPlan));
        window.location.href = '/#add-trade';
    });
    renderHistory();
    updateStopMode();
}
