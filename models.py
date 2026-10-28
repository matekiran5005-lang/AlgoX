"""
MongoDB data models and helpers for AlgoX.

Collections
-----------
users      – User credentials, demo-capital, algo status
trades     – Per-user trade log entries
strategy   – Global strategy configuration (admin-editable)
alerts     – System alert log
"""
from datetime import datetime, date
from config import Config


def _today_str() -> str:
    """Return today's date as ``DD Mon`` e.g. ``"26 Oct"``."""
    return datetime.now().strftime("%d %b")


def _today_date() -> str:
    """Return today's date as ``YYYY-MM-DD``."""
    return datetime.now().strftime("%Y-%m-%d")


# ───── User ─────────────────────────────────────────────────
def create_or_update_user(mongo, user_id, client_id, access_token, is_demo=False):
    """Insert or update a user document in MongoDB."""
    user_data = {
        "user_id": user_id,
        "client_id": client_id,
        "access_token": access_token,
        "is_demo": is_demo,
        "algo_active": False,
        "capital": 0,
        "demo_capital": Config.DEMO_CAPITAL,
        "holdings": [],
        "positions": [],
        "today_pnl": 0.0,
        "created_at": datetime.now(),
        "last_login": datetime.now(),
    }
    mongo.db.users.update_one(
        {"user_id": user_id},
        {"$set": user_data},
        upsert=True,
    )
    return user_data


def set_user_status(mongo, user_id, **fields):
    """Update arbitrary fields on a user document."""
    if not fields:
        return
    mongo.db.users.update_one(
        {"user_id": user_id},
        {"$set": {**fields, "last_login": datetime.now()}},
    )


def get_user(mongo, user_id):
    """Retrieve a single user by user_id."""
    return mongo.db.users.find_one({"user_id": user_id})


def get_all_users(mongo):
    """Retrieve all users (for admin / multi-user)."""
    return list(mongo.db.users.find({}))


def get_user_count(mongo):
    """Count total registered users."""
    return mongo.db.users.count_documents({})


# ───── Trades ───────────────────────────────────────────────
TRADE_STATUS = {
    "OPEN": "OPEN",
    "SL_HIT": "SL_HIT",
    "TSL_EXIT": "TSL_EXIT",
    "MARKET_EXIT": "MARKET_EXIT",
    "TIME_EXIT": "TIME_EXIT",
}


def create_trade(mongo, trade_data):
    """Insert a trade log entry."""
    trade_data["created_at"] = datetime.now()
    result = mongo.db.trades.insert_one(trade_data)
    return str(result.inserted_id)


def update_trade(mongo, trade_id, **fields):
    """Update a trade entry."""
    from bson import ObjectId

    fields["updated_at"] = datetime.now()
    _id = trade_id if isinstance(trade_id, ObjectId) else ObjectId(trade_id)
    mongo.db.trades.update_one({"_id": _id}, {"$set": fields})


def get_trades_by_user(mongo, user_id, limit=100):
    """Return trade history for a user, newest first."""
    cursor = mongo.db.trades.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    return [doc for doc in cursor]




# ───── Strategy Config ──────────────────────────────────────
DEFAULT_STRATEGY = {
    "name": "NIFTY 9:45 CE Strategy",
    "lot_qty": Config.LOT_QTY,
    "budget": Config.BUDGET,
    "entry_price_min": Config.ENTRY_PRICE_MIN,
    "entry_price_max": Config.ENTRY_PRICE_MAX,
    "sl_points": Config.SL_POINTS,
    "tsl_levels": [
        {"trigger": Config.TSL_TRIGGER_1, "sl_offset": Config.TSL_SL_1},
        {"trigger": Config.TSL_TRIGGER_2, "sl_offset": Config.TSL_SL_2},
    ],
    "market_open": "09:45",
    "market_close": "15:30",
    "updated_at": datetime.now(),
    "updated_by": "system",
}


def get_strategy(mongo):
    """Retrieve the (singleton) strategy config. If none exists, create default."""
    doc = mongo.db.strategy.find_one({})
    if not doc:
        mongo.db.strategy.insert_one(DEFAULT_STRATEGY)
        return DEFAULT_STRATEGY
    return doc


def update_strategy(mongo, **fields):
    """Update the strategy config."""
    fields["updated_at"] = datetime.now()
    mongo.db.strategy.update_one({}, {"$set": fields}, upsert=True)


# ───── Alerts (system log) ──────────────────────────────────
def log_alert(mongo, level, message):
    """Insert a system alert and keep only the last 1000."""
    mongo.db.alerts.insert_one({
        "level": level,  # INFO / WARNING / ERROR
        "message": message,
        "timestamp": datetime.now(),
    })
    # Keep only the latest 1000 alerts
    count = mongo.db.alerts.count_documents({})
    if count > 1000:
        oldest = list(mongo.db.alerts.find({}).sort("timestamp", 1).limit(count - 1000))
        for doc in oldest:
            mongo.db.alerts.delete_one({"_id": doc["_id"]})


# ───── Seed Demo Data ──────────────────────────────────────
def seed_demo_trades(mongo, user_id):
    """
    Insert the two example demo trades for a demo user so the
    dashboard and trade history show meaningful sample data.

    Trades:
      26 Oct | 22700 CE | +940
      27 Oct | 22800 CE | -286
    """
    existing = list(mongo.db.trades.find({"user_id": user_id}))
    if existing:
        return  # don't re-seed if trades already exist

    demo_trades = [
        {
            "user_id": user_id,
            "date": "26 Oct",
            "strike": 22700,
            "option_type": "CE",
            "entry_price": 100,
            "exit_price": 120,
            "sl_price": 80,
            "quantity": 15,
            "pnl": 940,
            "status": "TSL_EXIT",
            "is_demo": True,
            "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "exit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "created_at": datetime.now(),
        },
        {
            "user_id": user_id,
            "date": "27 Oct",
            "strike": 22800,
            "option_type": "CE",
            "entry_price": 110,
            "exit_price": 90,
            "sl_price": 90,
            "quantity": 15,
            "pnl": -286,
            "status": "SL_HIT",
            "is_demo": True,
            "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "exit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "created_at": datetime.now(),
        },
    ]

    for trade in demo_trades:
        mongo.db.trades.insert_one(trade)

    log_alert(mongo, "INFO", f"Seeded {len(demo_trades)} demo trades for user {user_id}")