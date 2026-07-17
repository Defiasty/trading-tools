const specs={NQ:{point:20,tick:.25,name:'NQ'},MNQ:{point:2,tick:.25,name:'MNQ'},ES:{point:50,tick:.25,name:'ES'},MES:{point:5,tick:.25,name:'MES'}};
const $=id=>document.getElementById(id);
const els=['instrument','account','riskValue','riskMode','slMode','slPoints','entryPrice','stopPrice','direction','rr'].reduce((o,id)=>(o[id]=$(id),o),{});
const money=n=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',minimumFractionDigits:2}).format(n||0);
const num=n=>Number(n||0);
const roundTick=(value,tick)=>Math.round(value/tick)*tick;

function getInputs(){
 const account=num(els.account.value), riskInput=num(els.riskValue.value), rr=num(els.rr.value);
 const riskBudget=els.riskMode.value==='percent'?account*riskInput/100:riskInput;
 let slPoints=num(els.slPoints.value),entry=num(els.entryPrice.value),stop=num(els.stopPrice.value);
 if(els.slMode.value==='prices') slPoints=Math.abs(entry-stop);
 return {account,riskInput,riskBudget,rr,slPoints,entry,stop,instrument:els.instrument.value,direction:els.direction.value,mode:els.slMode.value};
}

function validate(v){
 if(v.account<=0)return 'Wielkość konta musi być większa od zera.';
 if(v.riskBudget<=0)return 'Ryzyko musi być większe od zera.';
 if(v.slPoints<=0)return 'Stop loss musi być większy od zera.';
 if(v.rr<=0)return 'RR musi być większe od zera.';
 if(v.mode==='prices'&&(v.entry<=0||v.stop<=0))return 'Wpisz poprawną cenę wejścia i stop lossa.';
 return '';
}

function calculate(save=false){
 const v=getInputs(), error=validate(v); $('error').classList.toggle('hidden',!error); $('error').textContent=error;
 if(error)return;
 const spec=specs[v.instrument],riskOne=v.slPoints*spec.point,contracts=Math.floor(v.riskBudget/riskOne),actual=contracts*riskOne,unused=Math.max(0,v.riskBudget-actual),profit=actual*v.rr,tpPoints=v.slPoints*v.rr;
 $('resultInstrument').textContent=v.instrument;$('contracts').textContent=contracts;$('contractsLabel').textContent=contracts===1?'kontrakt':'kontraktów';
 $('riskBudget').textContent=money(v.riskBudget);$('riskPerContract').textContent=money(riskOne);$('actualRisk').textContent=money(actual);$('actualPercent').textContent=((actual/v.account)*100).toFixed(2)+'%';$('potentialProfit').textContent=money(profit);$('unusedRisk').textContent=money(unused);$('planSl').textContent=v.slPoints.toFixed(2)+' pkt';$('pointValue').textContent=money(spec.point);$('takeProfit').textContent=tpPoints.toFixed(2)+' pkt';
 let tp=null; const showTp=v.mode==='prices'; $('tpPriceRow').classList.toggle('hidden',!showTp);
 if(showTp){tp=v.direction==='long'?v.entry+tpPoints:v.entry-tpPoints;tp=roundTick(tp,spec.tick);$('tpPrice').textContent=tp.toFixed(2)}
 const warning=$('warning');
 if(contracts<1){warning.textContent=`Przy tym stop lossie 1 ${v.instrument} ryzykuje ${money(riskOne)}, czyli więcej niż ustawiony limit ${money(v.riskBudget)}. Zmniejsz SL, zwiększ limit albo wybierz kontrakt Micro.`;warning.classList.remove('hidden')}
 else if(els.riskMode.value==='percent'&&v.riskInput>2){warning.textContent='Ustawiłeś ryzyko powyżej 2% konta. Sprawdź, czy jest to zgodne z Twoim planem.';warning.classList.remove('hidden')}
 else warning.classList.add('hidden');
 if(save)saveHistory({...v,riskOne,contracts,actual,profit,tp,time:new Date().toISOString()});
}

function saveHistory(row){let h=JSON.parse(localStorage.getItem('psc_history')||'[]');h.unshift(row);h=h.slice(0,20);localStorage.setItem('psc_history',JSON.stringify(h));renderHistory()}
function renderHistory(){const h=JSON.parse(localStorage.getItem('psc_history')||'[]'),body=$('historyBody');body.innerHTML='';$('emptyHistory').classList.toggle('hidden',h.length>0);h.forEach(r=>{const tr=document.createElement('tr');tr.innerHTML=`<td>${new Date(r.time).toLocaleString('pl-PL',{dateStyle:'short',timeStyle:'short'})}</td><td><strong>${r.instrument}</strong></td><td>${money(r.account)}</td><td>${r.slPoints.toFixed(2)} pkt</td><td>${money(r.riskBudget)}</td><td><strong>${r.contracts}</strong></td><td>${money(r.actual)}</td><td>${money(r.profit)}</td>`;body.appendChild(tr)})}
function updateSlMode(){const price=els.slMode.value==='prices';$('pointsWrap').classList.toggle('hidden',price);$('entryWrap').classList.toggle('hidden',!price);$('stopWrap').classList.toggle('hidden',!price);calculate(false)}

$('calculateBtn').addEventListener('click',()=>calculate(true));els.slMode.addEventListener('change',updateSlMode);Object.values(els).forEach(el=>el.addEventListener('input',()=>calculate(false)));$('clearHistory').addEventListener('click',()=>{localStorage.removeItem('psc_history');renderHistory()});
$('themeBtn').addEventListener('click',()=>{document.documentElement.classList.toggle('light');const light=document.documentElement.classList.contains('light');$('themeBtn').textContent=light?'☀':'☾';localStorage.setItem('psc_theme',light?'light':'dark')});
if(localStorage.getItem('psc_theme')==='light'){document.documentElement.classList.add('light');$('themeBtn').textContent='☀'}
renderHistory();updateSlMode();
