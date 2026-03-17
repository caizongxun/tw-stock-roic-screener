import pandas as pd
import numpy as np
from config import WACC_CONFIG


def calc_roic(income_df: pd.DataFrame, balance_df: pd.DataFrame) -> pd.Series:
    """
    計算 ROIC = NOPAT / Invested Capital
    NOPAT = 營業利益 * (1 - tax_rate)
    IC = 股東權益 + 長期借款 + 短期借款 - 現金
    """
    tax = WACC_CONFIG["tax_rate"]
    roic_list = []

    try:
        # 取得營業利益 (OperatingIncome)
        oi = income_df[income_df["type"] == "OperatingIncome"][["date", "value"]].copy()
        oi["date"] = pd.to_datetime(oi["date"]).dt.year
        oi = oi.groupby("date")["value"].sum()

        # 投入資本相關項目
        equity = balance_df[balance_df["type"] == "Total equity attributable to owners of parent"][["date", "value"]].copy()
        equity["date"] = pd.to_datetime(equity["date"]).dt.year
        equity = equity.groupby("date")["value"].last()

        lt_debt = balance_df[balance_df["type"] == "LongTermBorrowings"][["date", "value"]].copy()
        lt_debt["date"] = pd.to_datetime(lt_debt["date"]).dt.year
        lt_debt = lt_debt.groupby("date")["value"].last().fillna(0)

        st_debt = balance_df[balance_df["type"] == "ShortTermBorrowings"][["date", "value"]].copy()
        st_debt["date"] = pd.to_datetime(st_debt["date"]).dt.year
        st_debt = st_debt.groupby("date")["value"].last().fillna(0)

        cash = balance_df[balance_df["type"] == "CashAndCashEquivalents"][["date", "value"]].copy()
        cash["date"] = pd.to_datetime(cash["date"]).dt.year
        cash = cash.groupby("date")["value"].last().fillna(0)

        common_years = oi.index.intersection(equity.index)
        for year in common_years:
            nopat = oi.get(year, 0) * (1 - tax)
            ic = (equity.get(year, 0)
                  + lt_debt.get(year, 0)
                  + st_debt.get(year, 0)
                  - cash.get(year, 0))
            if ic > 0:
                roic_list.append({"year": year, "roic": nopat / ic, "ic": ic})
    except Exception:
        pass

    if not roic_list:
        return pd.DataFrame(columns=["year", "roic", "ic"])
    return pd.DataFrame(roic_list).set_index("year")


def calc_wacc(income_df: pd.DataFrame, balance_df: pd.DataFrame, beta: float) -> float:
    """
    計算 WACC
    """
    rf = WACC_CONFIG["risk_free_rate"]
    mrp = WACC_CONFIG["market_risk_premium"]
    tax = WACC_CONFIG["tax_rate"]
    default_rd = WACC_CONFIG["default_rd"]

    re = rf + beta * mrp  # CAPM 股權成本

    try:
        equity = balance_df[balance_df["type"] == "Total equity attributable to owners of parent"]["value"].iloc[-1]
        lt_debt = balance_df[balance_df["type"] == "LongTermBorrowings"]["value"].iloc[-1] if len(
            balance_df[balance_df["type"] == "LongTermBorrowings"]) > 0 else 0
        st_debt = balance_df[balance_df["type"] == "ShortTermBorrowings"]["value"].iloc[-1] if len(
            balance_df[balance_df["type"] == "ShortTermBorrowings"]) > 0 else 0

        total_debt = lt_debt + st_debt
        v = equity + total_debt
        if v <= 0:
            return re

        # 負債成本
        interest = income_df[income_df["type"] == "InterestExpense"]["value"].sum()
        rd = (interest / total_debt) if total_debt > 0 else default_rd
        rd = max(rd, 0.01)  # 最低 1%

        wacc = (equity / v) * re + (total_debt / v) * rd * (1 - tax)
        return wacc
    except Exception:
        return re


def calc_gross_margin(income_df: pd.DataFrame) -> float:
    """計算最近一年毛利率"""
    try:
        revenue = income_df[income_df["type"] == "Revenue"][["date", "value"]].copy()
        revenue["date"] = pd.to_datetime(revenue["date"]).dt.year
        revenue = revenue.groupby("date")["value"].sum()

        gross_profit = income_df[income_df["type"] == "GrossProfit"][["date", "value"]].copy()
        gross_profit["date"] = pd.to_datetime(gross_profit["date"]).dt.year
        gross_profit = gross_profit.groupby("date")["value"].sum()

        common = revenue.index.intersection(gross_profit.index)
        if len(common) == 0:
            return 0.0
        latest_year = max(common)
        gm = gross_profit[latest_year] / revenue[latest_year] if revenue[latest_year] > 0 else 0
        return gm
    except Exception:
        return 0.0


def calc_ic_growth(roic_df: pd.DataFrame) -> float:
    """計算 IC 近 3 年複合成長率"""
    try:
        if len(roic_df) < 2:
            return 0.0
        ic = roic_df["ic"].sort_index()
        years = len(ic) - 1
        cagr = (ic.iloc[-1] / ic.iloc[0]) ** (1 / years) - 1
        return cagr
    except Exception:
        return 0.0
