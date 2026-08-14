"use client";

import { useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Trade = { date: string; action: string; price: number; balance: number; shares: number };
type BacktestResult = {
  dates: string[]; prices: number[]; equity_curve: number[]; signals: boolean[];
  predicted_returns: number[]; prediction_dates: string[]; model: string; modelVersion?: string; lookBack: number;
  metrics: { totalReturn: number; winRate: number; maxDrawdown: number; sharpe: number }; trades: Trade[];
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [ticker, setTicker] = useState("2330.TW");
  const [startDate, setStartDate] = useState("2022-01-01");
  const [endDate, setEndDate] = useState(new Date().toISOString().slice(0, 10));
  const [capital, setCapital] = useState(100000);
  const [stopLoss, setStopLoss] = useState(5);
  const [takeProfit, setTakeProfit] = useState(15);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const equityData = useMemo(() => !result ? [] : result.dates.map((date, index) => ({ date, benchmark: result.prices[index] / result.prices[0], strategy: (result.equity_curve[index] ?? capital) / capital })), [result, capital]);
  const tradeData = useMemo(() => !result ? [] : result.dates.map((date, index) => {
    const buys = result.trades.filter((trade) => trade.date === date && trade.action.includes("BUY"));
    const sells = result.trades.filter((trade) => trade.date === date && (trade.action.includes("SELL") || trade.action.includes("STOP") || trade.action.includes("TAKE")));
    return { date, price: result.prices[index], buy: buys[0]?.price ?? null, sell: sells[0]?.price ?? null };
  }), [result]);
  const predictionData = useMemo(() => !result ? [] : result.prediction_dates.map((date, index) => ({ date, predictedReturn: result.predicted_returns[index] * 100 })), [result]);

  async function runBacktest() {
    setLoading(true); setError("");
    try {
      const response = await fetch(`${API_URL}/api/backtest`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, start_date: startDate, end_date: endDate, initial_capital: capital, stop_loss: stopLoss / 100, take_profit: takeProfit / 100 }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "回測失敗");
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "無法連線至後端 API");
    } finally { setLoading(false); }
  }

  return (
    <main className="shell">
      <header className="hero"><div><div className="eyebrow">AI QUANT · NEXT.JS</div><h1>📈 AI-Driven 雙因子量化回測系統</h1><p>Production LSTM：預訓練模型 → inference → MA20 / 成交量因子 → 回測。</p></div><div className="status">● LSTM Inference Ready</div></header>
      <section className="workspace">
        <aside className="panel controls">
          <h2>⚙️ 交易策略參數</h2>
          <label>股票代號<input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} /></label>
          <div className="two-col"><label>開始日期<input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} /></label><label>結束日期<input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} /></label></div>
          <label>初始本金<input type="number" min={10000} step={10000} value={capital} onChange={(e) => setCapital(Number(e.target.value))} /></label>
          <label>停損：{stopLoss}%<input type="range" min={1} max={20} value={stopLoss} onChange={(e) => setStopLoss(Number(e.target.value))} /></label>
          <label>停利：{takeProfit}%<input type="range" min={1} max={50} value={takeProfit} onChange={(e) => setTakeProfit(Number(e.target.value))} /></label>
          <small className="muted">模型訓練已移出 API。Look-back 60 日；特徵：Return / Close / Volume / RSI。</small>
          <button onClick={runBacktest} disabled={loading}>{loading ? "⏳ LSTM inference 與回測中..." : "🚀 執行 LSTM 全端回測"}</button>
          {error && <div className="error">❌ {error}</div>}
        </aside>
        <section className="content">
          {!result && !loading && <div className="empty panel"><div className="empty-icon">🤖</div><h2>準備執行 LSTM inference</h2><p>API 只載入已發布的模型，不會因每次回測重新訓練。</p></div>}
          {loading && <div className="empty panel"><div className="spinner" /><h2>正在執行 inference...</h2><p>正在查詢 PostgreSQL、建立序列、載入 LSTM 權重並執行回測。</p></div>}
          {result && !loading && <>
            <div className="kpis"><Metric title="模型" value={`${result.model} · ${result.lookBack}D`} /><Metric title="版本" value={result.modelVersion ?? "-"} /><Metric title="總報酬率" value={`${result.metrics.totalReturn.toFixed(2)}%`} /><Metric title="Sharpe" value={result.metrics.sharpe.toFixed(2)} /></div>
            <ChartCard title="💰 累積淨值走勢（LSTM 雙因子 vs Benchmark)"><ResponsiveContainer width="100%" height={340}><LineChart data={equityData}><CartesianGrid strokeDasharray="3 3" stroke="#263248" /><XAxis dataKey="date" minTickGap={45} stroke="#8b97aa" /><YAxis stroke="#8b97aa" /><Tooltip contentStyle={{ background: "#111827", border: "1px solid #334155" }} /><Legend /><Line type="monotone" dataKey="benchmark" name="Benchmark" stroke="#94a3b8" dot={false} strokeDasharray="5 5" /><Line type="monotone" dataKey="strategy" name="LSTM 雙因子策略" stroke="#facc15" dot={false} strokeWidth={2} /></LineChart></ResponsiveContainer></ChartCard>
            <ChartCard title="🤖 LSTM 預測報酬率"><ResponsiveContainer width="100%" height={280}><LineChart data={predictionData}><CartesianGrid strokeDasharray="3 3" stroke="#263248" /><XAxis dataKey="date" minTickGap={45} stroke="#8b97aa" /><YAxis tickFormatter={(value) => `${value.toFixed(1)}%`} stroke="#8b97aa" /><Tooltip formatter={(value) => `${Number(value).toFixed(3)}%`} contentStyle={{ background: "#111827", border: "1px solid #334155" }} /><Line type="monotone" dataKey="predictedReturn" name="預測報酬率" stroke="#a78bfa" dot={false} strokeWidth={2} /></LineChart></ResponsiveContainer></ChartCard>
            <ChartCard title="🎯 AI 買賣點精準標記"><ResponsiveContainer width="100%" height={340}><LineChart data={tradeData}><CartesianGrid strokeDasharray="3 3" stroke="#263248" /><XAxis dataKey="date" minTickGap={45} stroke="#8b97aa" /><YAxis stroke="#8b97aa" domain={["auto", "auto"]} /><Tooltip contentStyle={{ background: "#111827", border: "1px solid #334155" }} /><Legend /><Line type="monotone" dataKey="price" name="實際收盤價" stroke="#22d3ee" dot={false} /><Line type="monotone" dataKey="buy" name="買進" stroke="#4ade80" strokeWidth={0} dot={{ r: 5, fill: "#4ade80" }} /><Line type="monotone" dataKey="sell" name="賣出/停損利" stroke="#f87171" strokeWidth={0} dot={{ r: 5, fill: "#f87171" }} /></LineChart></ResponsiveContainer></ChartCard>
            <ChartCard title="📝 系統交易日誌">{result.trades.length === 0 ? <p className="muted">本次回測期間無任何交易發生。</p> : <div className="table-wrap"><table><thead><tr><th>日期</th><th>交易動作</th><th>成交價格</th><th>帳戶餘額</th><th>變動股數</th></tr></thead><tbody>{result.trades.map((trade, index) => <tr key={`${trade.date}-${index}`}><td>{trade.date}</td><td>{trade.action}</td><td>{trade.price.toFixed(2)}</td><td>{trade.balance.toLocaleString()}</td><td>{trade.shares.toLocaleString()}</td></tr>)}</tbody></table></div>}</ChartCard>
          </>}
        </section>
      </section>
    </main>
  );
}

function Metric({ title, value }: { title: string; value: string }) { return <div className="metric panel"><span>{title}</span><strong>{value}</strong></div>; }
function ChartCard({ title, children }: { title: string; children: React.ReactNode }) { return <section className="panel chart-card"><h2>{title}</h2>{children}</section>; }
