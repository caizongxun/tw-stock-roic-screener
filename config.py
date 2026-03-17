# ===== 選股條件設定 =====
SCREEN_CONFIG = {
    "min_gross_margin": 0.30,       # 毛利率 >= 30%
    "min_ic_growth_rate": 0.0,      # IC 年成長率 >= 0%
    "roic_wacc_spread": 0.0,        # ROIC - WACC >= 0 (可調整為正溢價)
    "min_years_data": 3,            # 至少需要 3 年財務資料
}

# ===== WACC 參數 =====
WACC_CONFIG = {
    "risk_free_rate": 0.015,        # 無風險利率 (10年期公債)
    "market_risk_premium": 0.05,    # 市場風險溢酬
    "default_beta": 1.0,            # 無法取得 Beta 時使用預設值
    "tax_rate": 0.20,               # 台灣企業稅率 20%
    "default_rd": 0.03,             # 無負債時預設負債成本
}

# ===== 回測設定 =====
BACKTEST_CONFIG = {
    "years": 5,                     # 回測年數
    "rebalance": "annual",          # 再平衡頻率: annual / buy_and_hold
    "initial_capital": 1_000_000,   # 初始資金 (NTD)
    "benchmark": "^TWII",           # 基準指數 (台灣加權指數)
}

# ===== FinMind API =====
FINMIND_TOKEN = ""  # 若有 token 可填入以提升 API 限制
