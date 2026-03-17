#!/usr/bin/env python3
"""
debug_fields.py - 印出指定股票的 FinMind 財報所有欄位名稱
用法: python debug_fields.py 2330
"""
import sys
import requests
from config import FINMIND_TOKEN

API = "https://api.finmindtrade.com/api/v4/data"
stock_id = sys.argv[1] if len(sys.argv) > 1 else "2330"

for ds in ["TaiwanStockFinancialStatements", "TaiwanStockBalanceSheet"]:
    params = {"dataset": ds, "data_id": stock_id,
              "start_date": "2022-01-01", "token": FINMIND_TOKEN}
    r = requests.get(API, params=params, timeout=30).json()
    if r["status"] == 200 and r["data"]:
        import pandas as pd
        df = pd.DataFrame(r["data"])
        print(f"\n=== {ds} ===")
        print(sorted(df["type"].unique().tolist()))
    else:
        print(f"\n=== {ds} === 無資料 (status={r['status']})")
