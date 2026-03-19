import pytest
from backtest_core import calculate_metrics

def test_calculate_metrics_positive_return():
    """測試正常獲利情況下的績效結算邏輯是否正確"""
    # 準備模擬資料 (Arrange)
    init_cap = 100000.0
    final_cap = 120000.0
    eq_curve = [100000.0, 110000.0, 105000.0, 120000.0]
    trades = [5000.0, -2000.0, 7000.0]  # 兩賺一賠

    # 執行函數 (Act)
    metrics = calculate_metrics(init_cap, final_cap, eq_curve, trades)

# 驗證結果 (Assert)
    # 使用 pytest.approx 容許極微小的浮點數誤差
    assert metrics["Total Return (%)"] == pytest.approx(20.0)  
    assert metrics["Win Rate (%)"] == pytest.approx(66.67, abs=0.01) # 容許 0.01 的誤差
    assert metrics["Max Drawdown (%)"] < 0

def test_calculate_metrics_zero_capital_error():
    """測試防呆機制：當本金為 0 時，是否正確拋出 ValueError"""
    with pytest.raises(ValueError, match="初始本金必須大於 0"):
        calculate_metrics(0, 1000, [0, 1000], [1000])