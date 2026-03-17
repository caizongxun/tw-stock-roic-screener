#!/usr/bin/env python3
"""
demo_backtest.py
使用預設的知名台股高 ROIC 股票進行回測示範
(不需要 FinMind API，直接使用 yfinance 取得股價)
"""
import os
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from calculator import calc_annual_return, calc_max_drawdown, calc_sharpe

os.makedirs("output", exist_ok=True)

# 預設一批歷史上 ROIC 優秀的台股 (供 demo 使用)
DEMO_STOCKS = [
    "2330",  # 台積電
    "2317",  # 鴻海
    "2454",  # 聯發科
    "3008",  # 大立光
    "2382",  # 廣達
    "2308",  # 台達電
    "2395",  # 研華
    "6415",  # 矽力-KY
    "3231",  # 緯創
    "2379",  # 瑞昱
    "2412",  # 中華電
    "4938",  # 和碩
]


def run_demo():
    years = 5
    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=years * 365)).strftime("%Y-%m-%d")

    print(f"[Demo 回測] {start_date} ~ {end_date}")
    print(f"股票清單: {DEMO_STOCKS}")

    all_prices = []
    for sid in DEMO_STOCKS:
        ticker = f"{sid}.TW"
        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if not df.empty:
                col = df[["Close"]].rename(columns={"Close": sid})
                all_prices.append(col)
        except Exception as e:
            print(f"  跳過 {sid}: {e}")

    if not all_prices:
        print("無法取得任何股價資料")
        return

    price_df = pd.concat(all_prices, axis=1).ffill().bfill().dropna(how="all")

    portfolio_daily = price_df.pct_change().dropna().mean(axis=1)
    portfolio_cum = (1 + portfolio_daily).cumprod()

    bench_df = yf.download("^TWII", start=start_date, end=end_date, progress=False)
    bench_ret = bench_df["Close"].pct_change().dropna()
    bench_cum = (1 + bench_ret).cumprod()

    common = portfolio_cum.index.intersection(bench_cum.index)
    portfolio_cum = portfolio_cum.loc[common]
    bench_cum = bench_cum.loc[common]

    port_cagr = calc_annual_return(portfolio_cum)
    port_mdd = calc_max_drawdown(portfolio_cum)
    port_sharpe = calc_sharpe(portfolio_daily.loc[common])
    bench_cagr = calc_annual_return(bench_cum)
    bench_mdd = calc_max_drawdown(bench_cum)

    print("\n===== Demo 回測結果 =====")
    print(f"投資組合 CAGR:        {port_cagr*100:.2f}%")
    print(f"投資組合最大回撤:     {port_mdd*100:.2f}%")
    print(f"投資組合 Sharpe:      {port_sharpe:.2f}")
    print(f"台灣加權指數 CAGR:    {bench_cagr*100:.2f}%")
    print(f"超額報酬 (Alpha):     {(port_cagr - bench_cagr)*100:.2f}%")

    # 個股統計
    rows = []
    for sid in price_df.columns:
        s = price_df[sid].dropna()
        if len(s) < 2:
            continue
        tr = s.iloc[-1] / s.iloc[0] - 1
        cagr = calc_annual_return(s)
        mdd = calc_max_drawdown(s)
        rows.append({"stock_id": sid, "total_return": round(tr*100, 2),
                     "cagr": round(cagr*100, 2), "max_drawdown": round(mdd*100, 2)})

    result_df = pd.DataFrame(rows).sort_values("total_return", ascending=False)
    result_df.to_csv("output/demo_backtest_result.csv", index=False, encoding="utf-8-sig")
    print("\n個股報酬率:")
    print(result_df.to_string(index=False))

    # 圖表
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    axes[0].plot(portfolio_cum.index, portfolio_cum.values, label="ROIC 優質股組合",
                 color="#E8534B", linewidth=2)
    axes[0].plot(bench_cum.index, bench_cum.values, label="台灣加權指數",
                 color="#4B9CE8", linewidth=2, linestyle="--")
    axes[0].set_title(f"台股高 ROIC 策略 Demo ({years}年回測)", fontsize=14, fontweight="bold")
    axes[0].set_ylabel("累積報酬倍數")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    axes[0].xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.setp(axes[0].xaxis.get_majorticklabels(), rotation=45)

    colors = ["#E8534B" if r > 0 else "#4B9CE8" for r in result_df["total_return"]]
    axes[1].barh(result_df["stock_id"].astype(str), result_df["total_return"], color=colors)
    axes[1].axvline(x=0, color="black", linewidth=0.8)
    axes[1].set_title("個股5年總報酬率 (%)", fontsize=12, fontweight="bold")
    axes[1].set_xlabel("總報酬率 (%)")
    axes[1].grid(True, alpha=0.3, axis="x")

    plt.tight_layout()
    plt.savefig("output/demo_backtest_chart.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("\n圖表已儲存至 output/demo_backtest_chart.png")


if __name__ == "__main__":
    run_demo()
