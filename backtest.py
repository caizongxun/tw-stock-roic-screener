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
from config import BACKTEST_CONFIG

os.makedirs("output", exist_ok=True)
plt.rcParams["font.sans-serif"] = ["Noto Sans CJK TC", "PingFang TC", "Microsoft JhengHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def get_price_data(stock_id: str, start: str, end: str) -> pd.DataFrame:
    ticker = f"{stock_id}.TW"
    try:
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        close = df[["Close"]].copy()
        close.columns = [stock_id]
        return close
    except Exception as e:
        print(f"  [WARN] {stock_id} 股價下載失敗: {e}")
        return pd.DataFrame()


def run_backtest(selected_csv: str = "output/selected_stocks.csv"):
    if not os.path.exists(selected_csv):
        print(f"[錯誤] 找不到 {selected_csv}，請先執行 screener.py")
        return

    df_stocks = pd.read_csv(selected_csv)
    stock_ids = df_stocks["stock_id"].astype(str).tolist()

    years      = BACKTEST_CONFIG["years"]
    end_date   = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=years * 365)).strftime("%Y-%m-%d")

    print(f"[回測期間] {start_date} ~ {end_date}")
    print(f"[個股數量] {len(stock_ids)} 檔")

    all_prices = []
    for sid in stock_ids:
        p = get_price_data(sid, start_date, end_date)
        if not p.empty:
            all_prices.append(p)

    if not all_prices:
        print("[錯誤] 無法取得任何股價資料")
        return

    price_df = pd.concat(all_prices, axis=1).ffill().bfill().dropna(how="all")

    portfolio_daily  = price_df.pct_change().dropna().mean(axis=1)
    portfolio_cum    = (1 + portfolio_daily).cumprod()

    bench_df  = yf.download(BACKTEST_CONFIG["benchmark"], start=start_date, end=end_date,
                             progress=False, auto_adjust=True)
    bench_ret = bench_df["Close"].pct_change().dropna()
    bench_cum = (1 + bench_ret).cumprod()

    common = portfolio_cum.index.intersection(bench_cum.index)
    portfolio_cum = portfolio_cum.loc[common]
    bench_cum     = bench_cum.loc[common]

    # 個股統計
    stock_results = []
    for sid in price_df.columns:
        s = price_df[sid].dropna()
        if len(s) < 2:
            continue
        tr     = s.iloc[-1] / s.iloc[0] - 1
        cagr   = calc_annual_return(s)
        mdd    = calc_max_drawdown(s)
        sharpe = calc_sharpe(s.pct_change().dropna())
        stock_results.append({
            "stock_id":     sid,
            "start_price":  round(float(s.iloc[0]), 2),
            "end_price":    round(float(s.iloc[-1]), 2),
            "total_return": round(tr * 100, 2),
            "cagr":         round(cagr * 100, 2),
            "max_drawdown": round(mdd * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
        })

    result_df = pd.DataFrame(stock_results).sort_values("total_return", ascending=False)
    result_df.to_csv("output/backtest_result.csv", index=False, encoding="utf-8-sig")

    port_cagr   = calc_annual_return(portfolio_cum)
    port_mdd    = calc_max_drawdown(portfolio_cum)
    port_sharpe = calc_sharpe(portfolio_daily.loc[common])
    bench_cagr  = calc_annual_return(bench_cum)
    bench_mdd   = calc_max_drawdown(bench_cum)

    print("\n===== 回測結果 =====")
    print(f"投資組合 CAGR:        {port_cagr*100:.2f}%")
    print(f"投資組合最大回撤:     {port_mdd*100:.2f}%")
    print(f"投資組合 Sharpe:      {port_sharpe:.2f}")
    print(f"台灣加權指數 CAGR:    {bench_cagr*100:.2f}%")
    print(f"超額報酬 (Alpha):     {(port_cagr - bench_cagr)*100:.2f}%")

    # 繪圖
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    axes[0].plot(portfolio_cum.index, portfolio_cum.values,
                 label="ROIC>WACC 組合", color="#E8534B", linewidth=2)
    axes[0].plot(bench_cum.index, bench_cum.values,
                 label="台灣加權指數", color="#4B9CE8", linewidth=2, linestyle="--")
    axes[0].set_title(f"台股 ROIC>WACC 策略 vs 大盤 ({years}年回測)", fontsize=14, fontweight="bold")
    axes[0].set_ylabel("累積報酬倍數")
    axes[0].legend(); axes[0].grid(True, alpha=0.3)
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    axes[0].xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.setp(axes[0].xaxis.get_majorticklabels(), rotation=45)

    top20  = result_df.head(20)
    colors = ["#E8534B" if r > 0 else "#4B9CE8" for r in top20["total_return"]]
    axes[1].barh(top20["stock_id"].astype(str), top20["total_return"], color=colors)
    axes[1].axvline(x=0, color="black", linewidth=0.8)
    axes[1].set_title("個股總報酬率 (前20名, %)", fontsize=12, fontweight="bold")
    axes[1].set_xlabel("總報酬率 (%)")
    axes[1].grid(True, alpha=0.3, axis="x")

    plt.tight_layout()
    plt.savefig("output/backtest_chart.png", dpi=150, bbox_inches="tight")
    plt.close()
    print("\n[完成] 圖表已儲存至 output/backtest_chart.png")
    print("[完成] 個股報酬明細已儲存至 output/backtest_result.csv")
    return result_df


if __name__ == "__main__":
    run_backtest()
