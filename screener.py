import os
import time
import logging
import pandas as pd
from tqdm import tqdm
from data_fetcher import get_stock_list, get_financial_statements, get_beta
from calculator import calc_roic, calc_wacc, calc_gross_margin, calc_ic_growth
from config import SCREEN_CONFIG

os.makedirs("output", exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def screen_stock(stock_id: str) -> dict | None:
    try:
        data = get_financial_statements(stock_id)
        income_df  = data.get("income",  pd.DataFrame())
        balance_df = data.get("balance", pd.DataFrame())

        if income_df.empty or balance_df.empty:
            log.debug(f"{stock_id}: 財報資料為空")
            return None

        roic_df = calc_roic(income_df, balance_df)
        if roic_df.empty or len(roic_df) < SCREEN_CONFIG["min_years_data"]:
            log.debug(f"{stock_id}: ROIC 資料不足 (years={len(roic_df)})")
            return None

        latest_roic  = float(roic_df["roic"].iloc[-1])
        beta         = get_beta(stock_id)
        wacc         = calc_wacc(income_df, balance_df, beta)
        gross_margin = calc_gross_margin(income_df)
        ic_growth    = calc_ic_growth(roic_df)
        spread       = latest_roic - wacc

        log.info(f"{stock_id}: ROIC={latest_roic:.2%} WACC={wacc:.2%} spread={spread:.2%} "
                 f"GM={gross_margin:.2%} IC_growth={ic_growth:.2%}")

        if (
            spread       >= SCREEN_CONFIG["roic_wacc_spread"]
            and ic_growth    >= SCREEN_CONFIG["min_ic_growth_rate"]
            and gross_margin >= SCREEN_CONFIG["min_gross_margin"]
        ):
            return {
                "stock_id":        stock_id,
                "roic":            round(latest_roic,  4),
                "wacc":            round(wacc,          4),
                "roic_wacc_spread": round(spread,        4),
                "ic_growth":       round(ic_growth,     4),
                "gross_margin":    round(gross_margin,  4),
                "beta":            round(beta,          2),
            }
    except Exception as e:
        log.warning(f"{stock_id}: 例外 - {e}")
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
            print(f"[通過] {sid} ROIC={result['roic']:.2%} WACC={result['wacc']:.2%} "
                  f"GM={result['gross_margin']:.2%}")
        time.sleep(0.35)  # 避免 API rate limit

    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values("roic_wacc_spread", ascending=False)
        df.to_csv("output/selected_stocks.csv", index=False, encoding="utf-8-sig")
        print(f"\n[完成] 篩選出 {len(df)} 檔股票，已儲存至 output/selected_stocks.csv")
        print(df.to_string(index=False))
    else:
        print("[警告] 無符合條件的股票 - 請嘗試降低篩選門檻")
        print("建議：毛利率從 30% 降至 20%，或移除 IC 成長率限制")
    return df


if __name__ == "__main__":
    run_screener()
