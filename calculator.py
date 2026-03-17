import pandas as pd
import numpy as np
from config import WACC_CONFIG

# ===== FinMind TaiwanStockFinancialStatements 實際欄位名稱對照 =====
# 可用 python debug_fields.py 印出所有欄位確認
FIELD_MAP = {
    "operating_income": ["OperatingIncome", "營業利益（損失）", "營業利益"],
    "revenue":          ["Revenue", "營業收入合計", "營業收入淨額"],
    "gross_profit":     ["GrossProfit", "營業毛利（毛損）", "營業毛利"],
    "interest_expense": ["InterestExpense", "利息費用", "財務成本"],
}

BALANCE_MAP = {
    "equity":   ["Total equity attributable to owners of parent",
                 "歸屬於母公司業主之權益合計", "股東權益合計", "權益總計"],
    "lt_debt":  ["LongTermBorrowings", "長期借款", "長期負債"],
    "st_debt":  ["ShortTermBorrowings", "短期借款"],
    "cash":     ["CashAndCashEquivalents", "現金及約當現金"],
}


def _find_field(df: pd.DataFrame, candidates: list) -> pd.DataFrame:
    """嘗試多個欄位名稱，回傳第一個有資料的子集"""
    for name in candidates:
        sub = df[df["type"] == name]
        if not sub.empty:
            return sub
    return pd.DataFrame()


def _to_annual(df: pd.DataFrame) -> pd.Series:
    """將 date 欄位轉為年份並彙總 sum"""
    if df.empty:
        return pd.Series(dtype=float)
    d = df[["date", "value"]].copy()
    d["date"] = pd.to_datetime(d["date"]).dt.year
    return d.groupby("date")["value"].sum()


def _to_annual_last(df: pd.DataFrame) -> pd.Series:
    """取每年最後一筆（適合資產負債表）"""
    if df.empty:
        return pd.Series(dtype=float)
    d = df[["date", "value"]].copy()
    d["date"] = pd.to_datetime(d["date"]).dt.year
    return d.groupby("date")["value"].last()


def calc_roic(income_df: pd.DataFrame, balance_df: pd.DataFrame) -> pd.DataFrame:
    """
    ROIC = NOPAT / Invested Capital
    NOPAT = 營業利益 * (1 - tax)
    IC    = 股東權益 + 有息負債 - 現金
    """
    tax = WACC_CONFIG["tax_rate"]
    roic_list = []

    oi    = _to_annual(_find_field(income_df, FIELD_MAP["operating_income"]))
    eq    = _to_annual_last(_find_field(balance_df, BALANCE_MAP["equity"]))
    lt    = _to_annual_last(_find_field(balance_df, BALANCE_MAP["lt_debt"])).reindex(eq.index, fill_value=0)
    st    = _to_annual_last(_find_field(balance_df, BALANCE_MAP["st_debt"])).reindex(eq.index, fill_value=0)
    cash  = _to_annual_last(_find_field(balance_df, BALANCE_MAP["cash"])).reindex(eq.index, fill_value=0)

    if oi.empty or eq.empty:
        return pd.DataFrame(columns=["year", "roic", "ic"])

    common = oi.index.intersection(eq.index)
    for year in common:
        nopat = oi[year] * (1 - tax)
        ic = eq[year] + lt.get(year, 0) + st.get(year, 0) - cash.get(year, 0)
        if ic > 0:
            roic_list.append({"year": year, "roic": nopat / ic, "ic": ic})

    if not roic_list:
        return pd.DataFrame(columns=["year", "roic", "ic"])
    return pd.DataFrame(roic_list).set_index("year")


def calc_wacc(income_df: pd.DataFrame, balance_df: pd.DataFrame, beta: float) -> float:
    rf  = WACC_CONFIG["risk_free_rate"]
    mrp = WACC_CONFIG["market_risk_premium"]
    tax = WACC_CONFIG["tax_rate"]
    default_rd = WACC_CONFIG["default_rd"]

    re = rf + beta * mrp

    eq_s  = _find_field(balance_df, BALANCE_MAP["equity"])
    lt_s  = _find_field(balance_df, BALANCE_MAP["lt_debt"])
    st_s  = _find_field(balance_df, BALANCE_MAP["st_debt"])
    int_s = _find_field(income_df,  FIELD_MAP["interest_expense"])

    if eq_s.empty:
        return re

    equity     = float(eq_s["value"].iloc[-1])
    lt_debt    = float(lt_s["value"].iloc[-1]) if not lt_s.empty else 0.0
    st_debt    = float(st_s["value"].iloc[-1]) if not st_s.empty else 0.0
    total_debt = lt_debt + st_debt
    v = equity + total_debt
    if v <= 0:
        return re

    interest = float(int_s["value"].sum()) if not int_s.empty else 0.0
    rd = (interest / total_debt) if total_debt > 0 else default_rd
    rd = max(abs(rd), 0.01)

    wacc = (equity / v) * re + (total_debt / v) * rd * (1 - tax)
    return wacc


def calc_gross_margin(income_df: pd.DataFrame) -> float:
    rev_s = _to_annual(_find_field(income_df, FIELD_MAP["revenue"]))
    gp_s  = _to_annual(_find_field(income_df, FIELD_MAP["gross_profit"]))

    if rev_s.empty or gp_s.empty:
        return 0.0

    common = rev_s.index.intersection(gp_s.index)
    if len(common) == 0:
        return 0.0
    y = max(common)
    return gp_s[y] / rev_s[y] if rev_s[y] > 0 else 0.0


def calc_ic_growth(roic_df: pd.DataFrame) -> float:
    if roic_df.empty or len(roic_df) < 2:
        return 0.0
    ic = roic_df["ic"].sort_index()
    years = len(ic) - 1
    if ic.iloc[0] <= 0:
        return 0.0
    return (ic.iloc[-1] / ic.iloc[0]) ** (1 / years) - 1


# ===== 回測共用函數（backtest.py / demo_backtest.py 皆 import 此處）=====
def calc_annual_return(prices: pd.Series) -> float:
    if len(prices) < 2:
        return 0.0
    total = prices.iloc[-1] / prices.iloc[0] - 1
    years = (prices.index[-1] - prices.index[0]).days / 365.25
    if years <= 0:
        return 0.0
    return (1 + total) ** (1 / years) - 1


def calc_max_drawdown(prices: pd.Series) -> float:
    roll_max = prices.cummax()
    dd = (prices - roll_max) / roll_max
    return float(dd.min())


def calc_sharpe(returns: pd.Series, rf_annual: float = 0.015) -> float:
    rf_daily = (1 + rf_annual) ** (1 / 252) - 1
    excess = returns - rf_daily
    std = excess.std()
    if std == 0:
        return 0.0
    return float((excess.mean() / std) * np.sqrt(252))
