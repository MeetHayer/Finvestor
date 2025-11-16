export function SMA(values, period) {
  const out = Array(values.length).fill(null);
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    const v = Number(values[i]);
    if (!Number.isFinite(v)) { out[i] = null; continue; }
    sum += v;
    if (i >= period) sum -= Number(values[i - period]);
    if (i >= period - 1) out[i] = sum / period;
  }
  return out;
}

export function EMA(values, period) {
  const out = Array(values.length).fill(null);
  const k = 2 / (period + 1);
  let ema = null;
  for (let i = 0; i < values.length; i++) {
    const v = Number(values[i]);
    if (!Number.isFinite(v)) { out[i] = null; continue; }
    ema = ema == null ? v : v * k + ema * (1 - k);
    if (i >= period - 1) out[i] = ema;
  }
  return out;
}

export function RSI(values, period = 14) {
  const out = Array(values.length).fill(null);
  if (values.length < period + 1) return out;

  let gains = 0, losses = 0;
  for (let i = 1; i <= period; i++) {
    const diff = Number(values[i]) - Number(values[i - 1]);
    if (diff >= 0) gains += diff; else losses -= diff;
  }
  let avgGain = gains / period;
  let avgLoss = losses / period;
  out[period] = avgLoss === 0 ? 100 : 100 - (100 / (1 + (avgGain / avgLoss)));

  for (let i = period + 1; i < values.length; i++) {
    const diff = Number(values[i]) - Number(values[i - 1]);
    const gain = Math.max(diff, 0);
    const loss = Math.max(-diff, 0);
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    out[i] = avgLoss === 0 ? 100 : 100 - (100 / (1 + (avgGain / avgLoss)));
  }
  return out;
}



