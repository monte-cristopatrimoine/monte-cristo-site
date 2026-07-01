const PRODUCTS = {
  'p-av-libre':   { fees: 2.78 },
  'p-av-pilotee': { fees: 3.48 },
  'p-structures': { fees: 4.00 },
  'p-scpi':       { fees: 3.18 },
  'p-per':        { fees: 2.98 }
};

const MCP_FEES = 2.00;

function fmt(n) {
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(Math.round(n)) + ' €';
}

function pct(n) {
  return n.toFixed(2).replace('.', ',') + ' %';
}

function getAnalogy(diff) {
  if (diff < 15000)  return `Soit ${fmt(diff)} de plus — l'équivalent d'un voyage autour du monde.`;
  if (diff < 40000)  return `Soit ${fmt(diff)} de plus — l'équivalent d'une voiture neuve.`;
  if (diff < 80000)  return `Soit ${fmt(diff)} de plus — l'équivalent d'un apport immobilier solide.`;
  if (diff < 150000) return `Soit ${fmt(diff)} de plus — l'équivalent d'un studio dans une grande ville.`;
  if (diff < 300000) return `Soit ${fmt(diff)} de plus — l'équivalent d'un appartement en province.`;
  return `Soit ${fmt(diff)} de plus — l'équivalent d'une résidence secondaire.`;
}

function compute() {
  const capital   = parseFloat(document.getElementById('capital').value)   || 200000;
  const rendement = parseFloat(document.getElementById('rendement').value) || 5;
  const duree     = parseInt(document.getElementById('duree').value)       || 15;

  const selected = Object.keys(PRODUCTS).filter(id => document.getElementById(id).checked);
  if (selected.length === 0) return;

  const avgFees  = selected.reduce((s, id) => s + PRODUCTS[id].fees, 0) / selected.length;

  const bFactor  = (1 + rendement / 100) * (1 - avgFees  / 100);
  const mFactor  = (1 + rendement / 100) * (1 - MCP_FEES / 100);
  const bCapital = capital * Math.pow(bFactor, duree);
  const mCapital = capital * Math.pow(mFactor, duree);
  const bNetRate = (bFactor - 1) * 100;
  const mNetRate = (mFactor - 1) * 100;

  const gross  = capital * Math.pow(1 + rendement / 100, duree);
  const diff   = mCapital - bCapital;
  const saving = avgFees - MCP_FEES;

  document.getElementById('bank-rate-display').textContent   = pct(avgFees) + ' / an';
  document.getElementById('saving-rate-display').textContent = pct(saving > 0 ? saving : 0);
  document.getElementById('b-fees').textContent    = pct(avgFees);
  document.getElementById('b-start').textContent   = fmt(capital);
  document.getElementById('b-net').textContent     = pct(bNetRate);
  document.getElementById('b-capital').textContent = fmt(bCapital);
  document.getElementById('b-cost').textContent    = 'Manque à gagner estimé : ~' + fmt(gross - bCapital);
  document.getElementById('m-start').textContent   = fmt(capital);
  document.getElementById('m-net').textContent     = pct(mNetRate);
  document.getElementById('m-capital').textContent = fmt(mCapital);
  document.getElementById('m-cost').textContent    = 'Manque à gagner estimé : ~' + fmt(gross - mCapital);
  document.querySelectorAll('#b-duree-lbl, #m-duree-lbl').forEach(el => el.textContent = duree);
  document.getElementById('diff-val').textContent  = '+ ' + fmt(diff);
  document.getElementById('analogy-bar').textContent = getAnalogy(diff);

  drawChart(capital, bFactor, mFactor, duree);
}

function drawChart(capital, bFactor, mFactor, duree) {
  const canvas = document.getElementById('chart');
  const dpr = window.devicePixelRatio || 1;
  const W = Math.max(100, (canvas.closest('.sim-chart') || canvas.parentElement).offsetWidth - 64);
  const H = 240;
  canvas.width  = W * dpr;
  canvas.height = H * dpr;
  canvas.style.width  = W + 'px';
  canvas.style.height = H + 'px';

  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, W, H);

  const pad = { top: 16, right: 16, bottom: 36, left: 72 };
  const cW = W - pad.left - pad.right;
  const cH = H - pad.top - pad.bottom;

  const bSeries = [], mSeries = [];
  for (let y = 0; y <= duree; y++) {
    bSeries.push(capital * Math.pow(bFactor, y));
    mSeries.push(capital * Math.pow(mFactor, y));
  }

  const maxVal = Math.max(...mSeries) * 1.05;
  const minVal = Math.min(capital * 0.9, ...bSeries);

  function xPos(i)   { return pad.left + (i / duree) * cW; }
  function yPos(val) { return pad.top + cH - ((val - minVal) / (maxVal - minVal)) * cH; }

  // Grid
  ctx.strokeStyle = '#E8E1CC'; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = pad.top + (i / 4) * cH;
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(pad.left + cW, y); ctx.stroke();
    const val = maxVal - (i / 4) * (maxVal - minVal);
    ctx.fillStyle = '#6B6359';
    ctx.font = '11px "Creato Display", system-ui, sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText((val / 1000).toFixed(0) + 'k', pad.left - 10, y + 4);
  }

  // X labels
  ctx.fillStyle = '#6B6359';
  ctx.font = '11px "Creato Display", system-ui, sans-serif';
  ctx.textAlign = 'center';
  const step = duree <= 20 ? 5 : 10;
  for (let y = 0; y <= duree; y += step) {
    ctx.fillText('an ' + y, xPos(y), H - pad.bottom + 18);
  }

  // Gap fill (green tint between curves)
  ctx.beginPath();
  mSeries.forEach((v, i) => i === 0 ? ctx.moveTo(xPos(i), yPos(v)) : ctx.lineTo(xPos(i), yPos(v)));
  for (let i = duree; i >= 0; i--) ctx.lineTo(xPos(i), yPos(bSeries[i]));
  ctx.closePath();
  ctx.fillStyle = 'rgba(52, 104, 72, 0.08)'; ctx.fill();

  // Bank line (dashed muted)
  ctx.beginPath();
  ctx.strokeStyle = '#6B6359';
  ctx.lineWidth = 2;
  ctx.setLineDash([5, 4]);
  bSeries.forEach((v, i) => i === 0 ? ctx.moveTo(xPos(i), yPos(v)) : ctx.lineTo(xPos(i), yPos(v)));
  ctx.stroke();
  ctx.setLineDash([]);

  // MCP line (solid green)
  ctx.beginPath();
  ctx.strokeStyle = '#346848';
  ctx.lineWidth = 2.5;
  mSeries.forEach((v, i) => i === 0 ? ctx.moveTo(xPos(i), yPos(v)) : ctx.lineTo(xPos(i), yPos(v)));
  ctx.stroke();

  // End dots
  ctx.fillStyle = '#6B6359';
  ctx.beginPath();
  ctx.arc(xPos(duree), yPos(bSeries[duree]), 4, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = '#346848';
  ctx.beginPath();
  ctx.arc(xPos(duree), yPos(mSeries[duree]), 5.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#FDFAF3';
  ctx.beginPath();
  ctx.arc(xPos(duree), yPos(mSeries[duree]), 2, 0, Math.PI * 2);
  ctx.fill();

  // End labels (small)
  ctx.font = '600 11px "Creato Display", system-ui, sans-serif';
  ctx.textAlign = 'right';
  ctx.fillStyle = '#346848';
  ctx.fillText(fmt(mSeries[duree]), xPos(duree) - 4, yPos(mSeries[duree]) - 10);
  ctx.fillStyle = '#6B6359';
  ctx.fillText(fmt(bSeries[duree]), xPos(duree) - 4, yPos(bSeries[duree]) + 16);
}

document.getElementById('rendement').addEventListener('input', function() {
  document.getElementById('rendement-val').textContent = this.value;
  this.setAttribute('aria-valuetext', this.value + ' % par an');
  compute();
});
document.getElementById('duree').addEventListener('input', function() {
  document.getElementById('duree-val').textContent = this.value;
  this.setAttribute('aria-valuetext', this.value + ' ans');
  compute();
});
document.getElementById('capital').addEventListener('input', compute);
Object.keys(PRODUCTS).forEach(id => document.getElementById(id).addEventListener('change', compute));

function initCompute() {
  const container = document.querySelector('.sim-chart');
  if (container && container.offsetWidth > 0) { compute(); }
  else { requestAnimationFrame(initCompute); }
}
if (document.readyState === 'complete') { initCompute(); }
else { window.addEventListener('load', initCompute); }
window.addEventListener('resize', compute);
