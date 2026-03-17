# 台股選股程式：ROIC > WACC 策略回測

## 選股條件
- **ROIC > WACC**：投入資本回報率 > 加權平均資本成本
- **IC 成長率 > 0**：投入資本逐年成長（代表公司持續擴張）
- **毛利率 > 30%**：具備競爭護城河

## 資料來源
- [FinMind](https://finmindtrade.com/) 台股財務資料（免費 API）
- yfinance 補充股價資料

## 安裝
```bash
pip install -r requirements.txt
```

## 使用方式
```bash
# 1. 選股
python screener.py

# 2. 回測（5年）
python backtest.py
```

## 輸出
- `output/selected_stocks.csv`：符合條件的個股清單
- `output/backtest_result.csv`：回測報酬率結果
- `output/backtest_chart.png`：累積報酬率走勢圖

## ROIC / WACC 計算方式

### ROIC
```
ROIC = NOPAT / Invested Capital
NOPAT = 營業利益 × (1 - 稅率)
Invested Capital = 股東權益 + 有息負債 - 非營業資產
```

### WACC
```
WACC = (E/V × Re) + (D/V × Rd × (1-T))
Re (股權成本) = 無風險利率 + Beta × 市場風險溢酬
  無風險利率 = 1.5%（10年期公債殖利率）
  市場風險溢酬 = 5%
Rd (負債成本) = 利息費用 / 有息負債
```
