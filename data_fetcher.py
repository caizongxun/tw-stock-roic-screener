import requests
import pandas as pd
import yfinance as yf
from config import FINMIND_TOKEN

FINMIND_API = "https://api.finmindtrade.com/api/v4/data"


def get_stock_list() -> list:
    """取得上市上櫃股票清單"""
    params = {
        "dataset": "TaiwanStockInfo",
        "token": FINMIND_TOKEN,
    }
    resp = requests.get(FINMIND_API, params=params, timeout=30)
    data = resp.json()
    if data["status"] != 200:
        raise RuntimeError(f"FinMind API error: {data}")
    df = pd.DataFrame(data["data"])
    # 只保留一般股票(排除 ETF、特別股)
    df = df[df["type"].isin(["twse", "otc"])]
    return df["stock_id"].tolist()


def get_financial_statements(stock_id: str, start_date: str = "2018-01-01") -> dict:
    """
    取得財務報表資料
    returns: dict with keys: income, balance, cashflow
    """
    result = {}
    datasets = {
        "income": "TaiwanStockFinancialStatements",
        "balance": "TaiwanStockBalanceSheet",
    }
    for key, dataset in datasets.items():
        params = {
            "dataset": dataset,
            "data_id": stock_id,
            "start_date": start_date,
            "token": FINMIND_TOKEN,
        }
        try:
            resp = requests.get(FINMIND_API, params=params, timeout=30)
            data = resp.json()
            if data["status"] == 200 and data["data"]:
                result[key] = pd.DataFrame(data["data"])
            else:
                result[key] = pd.DataFrame()
        except Exception:
            result[key] = pd.DataFrame()
    return result


def get_stock_price(stock_id: str, period: str = "5y") -> pd.DataFrame:
    """使用 yfinance 取得股價資料"""
    ticker = f"{stock_id}.TW"
    try:
        df = yf.download(ticker, period=period, progress=False)
        return df
    except Exception:
        return pd.DataFrame()


def get_beta(stock_id: str) -> float:
    """取得 Beta 值"""
    from config import WACC_CONFIG
    ticker = f"{stock_id}.TW"
    try:
        info = yf.Ticker(ticker).info
        beta = info.get("beta", WACC_CONFIG["default_beta"])
        return beta if beta and beta > 0 else WACC_CONFIG["default_beta"]
    except Exception:
        return WACC_CONFIG["default_beta"]
