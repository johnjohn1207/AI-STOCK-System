"use client";

import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Trade = {
  date: string;
  action: string;
  price: number;
  balance: number;
  shares: number;
};

type BacktestResult = {
  dates: string[];
  prices: number[];
  equity_curve: number[];
  metrics: {
    totalReturn: number;
    winRate: number;
    maxDrawdown: number;
    sharpe: number;
  };
  trades: Trade[];
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

  const equityData = useMemo(() => {
    if (!result) return [];
    return result.dates.map((date, index) => ({
      date,
      benchmark: result.prices[index] / result.prices[0],
      strategy: (result.equity_curve[index] ?? capital) / capital,
    }));
  }, [result, capital]);

  const tradeData = useMemo(() => {
    if (!result) return [];
    return result.dates.map((date, index) => {
      const buys = result.trades.filter((trade) => trade.date === date && trade.action.includes("BUY"));
      const sells = result.trades.filter(
        (trade) => trade.date === date && (trade.action.includes("SELL") || trade.action.includes("STOP") || trade.action.includes("TAKE")),
      );
      return {
        date,
        price: result.prices[index],
        buy: buys[0]?.price ?? null,
        sell: sells[0]?.price ?? null,
      };
    });
  }, [result]);

  async function runBacktest() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_URL}/api/backtest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker,
          start_date: startDate,
          end_date: endDate,
          initial_capital: capital,
          stop_loss: stopLoss / 100,
          take_profit: takeProfit / 100,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? "回測失敗");
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "無法連線至後端 API");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <header className="hero">
        <div>
          <div className="eyebrow">AI QUANT · NEXT.JS</div>
          <h1>📈 AI-Driven 雙因子量化回測系統</h1>
          <p>結合 LSTM、PostgreSQL 與互動式市場分析，將原 Streamlit Dashboard 升級成現代化 Web App。</p>
        </div>
        <div className="status">● API Ready</div>
      </header>

      <section className="workspace">
        <aside className="panel controls">
          <h2>⚙️ 交易策略參數</h2>
          <label>股票代號<input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} /></label>
          <div className="two-col">
            <label>開始日期<input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} /></label>
            <label>結束日期<input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} /></label>
          </div>
          <label>初始本金<input type="number" min={10000} step={10000} value={capital} onChange={(e) => setCapital(Number(e.target.value))} /></label>
          <label>停損：{stopLoss}%<input type="range" min={1} max={20} value={stopLoss} onChange={(e) => setStopLoss(Number(e.target.value))} /></label>
          <label>停利：{takeProfit}%<input type="range" min={1} max={50} value={takeProfit} onChange={(e) => setTakeProfit(Number(e.target.value))} /></label>
          <button onClick={runBacktest} disabled={loading}>{loading ? "⏳ 執行中..." : "🚀 執行全端系統回測"}</button>
          {error && <div className="error">❌ {error}</div>}
        </aside>

        <section className="content">
          {!result && !loading && (
            <div className="empty panel"><div className="empty-icon">📊</div><h2>準備開始回測</h2><p>設定左側參數後，執行回測即可查看策略績效、資金曲線與交易明細。</p></div>
          )}

          {loading && <div className="empty panel"><div className="spinner" /><h2>正在執行 AI 回測...</h2><p>正在查詢 PostgreSQL 並計算策略績效。</p></div>}

          {result && !loading && (
            <>
              <div className="kpis">
                <Metric title="總報酬率" value={`${result.metrics.totalReturn.toFixed(2)}%`} />
                <Metric title="勝率" value={`${result.metrics.winRate.toFixed(2)}%`} />
                <Metric title="最大回撤 (MDD)" value={`${result.metrics.maxDrawdown.toFixed(2)}%`} />
                <Metric title="夏普值 (Sharpe)" value={result.metrics.sharpe.toFixed(2)} />
              </div>

              <ChartCard title="💰 累積淨值走勢（AI 策略 vs Benchmark）">
                <ResponsiveContainer width="100%" height={340}>
                  <LineChart data={equityData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#263248" />
                    <XAxis dataKey="date" minTickGap={45} stroke="#8b97aa" />
                    <YAxis stroke="#8b97aa" domain={[(dataMin: number) => Math.min(dataMin, 0.9), (dataMax: number) => Math.max(dataMax, 1.1)]} />
                    <Tooltip contentStyle={{ background: "#111827", border: "1px solid #334155" }} />
                    <Legend />
                    <Line type="monotone" dataKey="benchmark" name="Benchmark" stroke="#94a3b8" dot={false} strokeDasharray="5 5" />
                    <Line type="monotone" dataKey="strategy" name="AI 雙因子策略" stroke="#facc15" dot={false} strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="🎯 AI 買賣點精準標記">
                <ResponsiveContainer width="100%" height={340}>
                  <LineChart data={tradeData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#263248" />
                    <XAxis dataKey="date" minTickGap={45} stroke="#8b97aa" />
                    <YAxis stroke="#8b97aa" domain={["auto", "auto"]} />
                    <Tooltip contentStyle={{ background: "#111827", border: "1px solid #334155" }} />
                    <Legend />
                    <Line type="monotone" dataKey="price" name="實際收盤價" stroke="#22d3ee" dot={false} />
                    <Line type="monotone" dataKey="buy" name="買進" stroke="#4ade80" strokeWidth={0} dot={{ r: 5, fill: "#4ade80" }} connectNulls={false} />
                    <Line type="monotone" dataKey="sell" name="賣出/停損利" stroke="#f87171" strokeWidth={0} dot={{ r: 5, fill: "#f87171" }} connectNulls={false} />
                  </LineChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="📝 系統交易日誌">
                {result.trades.length === 0 ? <p className="muted">本次回測期間無任何交易發生。</p> : (
                  <div className="table-wrap"><table><thead><tr><th>日期</th><th>交易動作</th><th>成交價格</th><th>帳戶餘額</th><th>變動股數</th></tr></thead><tbody>
                    {result.trades.map((trade, index) => <tr key={`${trade.date}-${index}`}><td>{trade.date}</td><td>{trade.action}</td><td>{trade.price.toFixed(2)}</td><td>{trade.balance.toLocaleString()}</td><td>{trade.shares.toLocaleString()}</td></tr>)}
                  </tbody></table></div>
                )}
              </ChartCard>
            </>
          )}
        </section>
      </section>
    </main>
  );
}

function Metric({ title, value }: { title: string; value: string }) {
  return <div className="metric panel"><span>{title}</span><strong>{value}</strong></div>;
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="panel chart-card"><h2>{title}</h2>{children}</section>;
}
