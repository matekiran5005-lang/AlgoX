"""
Configuration for AlgoX - Multi-User Algo Trading Web App
NIFTY 9:45 Strategy
"""
import os
from datetime import time


class Config:
    # ─── Flask ───────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "algox-secret-key-2024-change-me")
    DEBUG = os.environ.get("FLASK_DEBUG", "true").lower() == "true"

    # ─── MongoDB ─────────────────────────────────────────────
    MONGO_URI = os.environ.get(
        "MONGO_URI", "mongodb://localhost:27017/algox"
    )

    # ─── Dhan HQ API ─────────────────────────────────────────
    DHAN_API_BASE = "https://api.dhan.co/v2"

    # ─── NIFTY Instrument Constants ─────────────────────────
    # NIFTY 50 index security id on Dhan
    NIFTY_UNDERLYING_SCRIP = 13
    # Index segment for fetching option chain
    NIFTY_SEGMENT = "IDX_I"
    # Exchange segment for NIFTY options (F&O)
    OPTION_EXCHANGE_SEGMENT = "NSE_FNO"
    # NIFTY strikes are in multiples of 50
    STRIKE_MULTIPLES = 50
    # Lot size: user specified 65; actual NIFTY lot is 15.
    # We honour the user's spec (65) but keep it configurable.
    LOT_QTY = int(os.environ.get("LOT_QTY", 65))

    # ─── Strategy Parameters (NIFTY 9:45) ────────────────────
    BUDGET = 10_000          # Max budget per trade in Rs
    ENTRY_PRICE_MIN = 100    # Min CE option entry price
    ENTRY_PRICE_MAX = 140    # Max CE option entry price
    SL_POINTS = 20           # Stop-loss: Entry - 20 points
    # Trailing Stop-Loss levels
    TSL_TRIGGER_1 = 20       # Price goes +20 → move SL to Entry + 10
    TSL_SL_1 = 10
    TSL_TRIGGER_2 = 40       # Price goes +40 → move SL to Entry + 30
    TSL_SL_2 = 30

    # ─── Market Timings (IST) ─────────────────────────────────
    MARKET_OPEN_TIME = time(9, 45)    # 9:45 AM – auto buy
    MARKET_CLOSE_TIME = time(15, 30)  # 3:30 PM – exit
    # Time to start monitoring after entry (seconds)
    MONITOR_INTERVAL = 30

    # ─── Demo / Paper Trading ─────────────────────────────────
    DEMO_CAPITAL = 10_000   # Virtual capital when demo mode is ON

    # ─── Server ───────────────────────────────────────────────
    PORT = int(os.environ.get("PORT", 3000))
    HOST = os.environ.get("HOST", "0.0.0.0")