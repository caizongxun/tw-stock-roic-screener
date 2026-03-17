import os
import time
import pandas as pd
from tqdm import tqdm
from data_fetcher import get_stock_list, get_financial_statements, get_beta
from calculator import calc_roic, calc_wacc, calc_gross_margin, calc_ic_growth
from config import SCREEN_CONFIG

os.makedirs("output", exist_ok=True)


def screen_stock(stock_id: str) -> dict | None:
    try:
        data = get_financial_statements(stock_id)
        if data["income"].empty or data["balance"].empty:
            return None

        roic_df = calc_roic(data["income"], data["balance"])
        if roic_df.empty or len(roic_df) < SCREEN_CONFIG["min_years_data"]:
            return None

        latest_roic = roic_df["roic"].iloc[-1]
        beta = get_beta(stock_id)
        wacc = calc_wacc(data["income"], data["balance"], beta)
        gross_margin = calc_gross_margin(data["income"])
        ic_growth = calc_ic_growth(roic_df)
        spread = latest_roic - wacc

        # 選股條件
        if (
            spread >= SCREEN_CONFIG["roic_wacc_spread"]
            and ic_growth >= SCREEN_CONFIG["min_ic_growth_rate"]
            and gross_margin >= SCREEN_CONFIG["min_gross_margin"]
        ):
            return {
                "stock_id": stock_id,
                "roic": round(latest_roic, 4),
                "wacc": round(wacc, 4),
                "roic_wacc_spread": round(spread, 4),
                "ic_growth": round(ic_growth, 4),
                "gross_margin": round(gross_margin, 4),
                "beta": round(beta, 2),
            }
    except Exception as e:
        pass
    return None


def run_screener():
    print("[1/3] 取得股票清單...")
    stocks = get_stock_list()
    print(f"共 {len(stocks)} 檔股票待篩選")

    results = []
    for sid in tqdm(stocks, desc="篩選中"):
        result = screen_stock(sid)
        if result:
            results.append(result)
        time.sleep(0.3)  # 避免 API rate limit

    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values("roic_wacc_spread", ascending=False)
        df.to_csv("output/selected_stocks.csv", index=False, encoding="utf-8-sig")
        print(f"\n[完成] 篩選出 {len(df)} 檔股票，已儲存至 output/selected_stocks.csv")
        print(df.to_string(index=False))
    else:
        print("[警告] 無符合條件的股票")
    return df


if __name__ == "__main__":
    run_screener()
