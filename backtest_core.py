import numpy as np
import pandas as pd
from typing import List, Dict, Union, Tuple, Any

def run_backtest(
    test_dates: Union[pd.DatetimeIndex, List], 
    backtest_prices: np.ndarray, 
    final_signals: np.ndarray, 
    ma20_data: np.ndarray, 
    factor_pass_data: np.ndarray, 
    initial_capital: float, 
    stop_loss_pct: float, 
    take_profit_pct: float
) -> Tuple[float, List[float], List[Tuple], List[float]]:
    """
    執行雙因子量化策略回測引擎。
    
    結合 AI 預測訊號、MA20 趨勢濾網與多因子動能指標，進行逐日推進 (Walk-forward) 的虛擬交易。

    Args:
        test_dates: 測試期間的日期陣列。
        backtest_prices: 測試期間的每日收盤價陣列。
        final_signals: AI 模型輸出的預測訊號陣列 (True 為看漲)。
        ma20_data: 20 日移動平均線陣列。
        factor_pass_data: 多因子審查結果陣列 (True 為通過審查)。
        initial_capital: 初始投入本金。
        stop_loss_pct: 停損百分比 (例如 0.05 代表 5%)。
        take_profit_pct: 停利百分比 (例如 0.15 代表 15%)。

    Returns:
        Tuple 包含:
        - final_capital (float): 期末最終總資產。
        - equity_curve (List[float]): 每日資產淨值曲線。
        - trade_log (List[Tuple]): 交易明細紀錄。
        - trade_profits (List[float]): 每筆交易的已實現損益。
    """
    capital = initial_capital
    position = 0
    trade_log = []
    equity_curve = [initial_capital]
    trade_profits = []
    entry_price = 0

    for i in range(len(final_signals) - 1):
        current_price = backtest_prices[i]
        next_price = backtest_prices[i+1]
        signal = final_signals[i]
        current_ma20 = ma20_data[i]
        current_factor_pass = factor_pass_data[i]

        # === 1. 持股狀態下的賣出判斷 ===
        if position > 0:
            current_ret = (current_price - entry_price) / entry_price

            if current_ret <= -stop_loss_pct:
                capital += position * current_price
                profit = (current_price - entry_price) * position
                trade_profits.append(profit)
                trade_log.append((test_dates[i], "STOP LOSS", current_price, capital, 0))
                position = 0

            elif current_ret >= take_profit_pct:
                capital += position * current_price
                profit = (current_price - entry_price) * position
                trade_profits.append(profit)
                trade_log.append((test_dates[i], "TAKE PROFIT", current_price, capital, 0))
                position = 0

            elif not signal:
                capital += position * current_price
                profit = (current_price - entry_price) * position
                trade_profits.append(profit)
                trade_log.append((test_dates[i], "SELL (AI Signal)", current_price, capital, 0))
                position = 0

        # === 2. 空手狀態下的買進判斷 ===
        elif signal and position == 0:
            if (current_price > current_ma20) and current_factor_pass:
                position = capital // current_price
                if position > 0:
                    capital -= position * current_price
                    entry_price = current_price
                    trade_log.append((test_dates[i], "BUY (AI + Multi-Factor)", current_price, capital, position))

        current_equity = capital + position * next_price
        equity_curve.append(current_equity)

    # 結算最後一天的部位
    if position > 0:
        final_price = backtest_prices[-1]
        capital += position * final_price
        profit = (final_price - entry_price) * position
        trade_profits.append(profit)
        trade_log.append((test_dates[-1], "FINAL SELL", final_price, capital, 0))

    return capital, equity_curve, trade_log, trade_profits


def calculate_metrics(
    initial_capital: float, 
    final_capital: float, 
    equity_curve: List[float], 
    trade_profits: List[float]
) -> Dict[str, Any]:
    """
    結算量化回測之綜合績效指標。

    Args:
        initial_capital: 初始本金。
        final_capital: 最終淨值。
        equity_curve: 每日淨值陣列。
        trade_profits: 交易獲利陣列。

    Returns:
        Dict 包含總報酬、夏普值、最大回撤、勝率與每日報酬率序列。
    """
    if initial_capital <= 0:
        raise ValueError("初始本金必須大於 0")
    total_return_pct = (final_capital / initial_capital - 1) * 100
    equity_series = pd.Series(equity_curve)
    strategy_returns = equity_series.pct_change().fillna(0).values 
    
    mean_ret = np.mean(strategy_returns)
    std_ret = np.std(strategy_returns) + 1e-9
    
    # 確保 NumPy scalar 正確轉換為 Python 原生型別
    if hasattr(mean_ret, 'item'): mean_ret = mean_ret.item()
    if hasattr(std_ret, 'item'): std_ret = std_ret.item()
    
    sharpe_val = (mean_ret / std_ret) * np.sqrt(252)
    if np.isnan(sharpe_val): sharpe_val = 0.0

    rolling_max = equity_series.cummax()
    drawdown = (equity_series - rolling_max) / rolling_max
    max_drawdown = drawdown.min() * 100 
    if hasattr(max_drawdown, 'item'): max_drawdown = max_drawdown.item()

    if len(trade_profits) > 0:
        win_rate = np.mean(np.array(trade_profits) > 0) * 100
    else:
        win_rate = 0.0
    if hasattr(win_rate, 'item'): win_rate = win_rate.item()

    return {
        "Total Return (%)": float(np.array(total_return_pct).item()),
        "Sharpe Ratio": float(sharpe_val),
        "Max Drawdown (%)": float(max_drawdown),
        "Win Rate (%)": float(win_rate),
        "Strategy Returns": strategy_returns
    }