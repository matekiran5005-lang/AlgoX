"""
Trading Engine for AlgoX – NIFTY 9:45 CE Strategy.

Responsibilities:
  • Register / deregister multi-user Dhan clients
  • At 9:45 AM IST – auto-buy ATM NIFTY CE (price 100–140, 1 lot)
  • Monitor positions every 30 s – SL / TSL trailing stop-loss
  • At 3:30 PM IST – exit all open positions
  • Paper-trading (demo) mode with virtual capital
  • APScheduler background for time-based triggers
"""
import threading
import logging
from datetime import datetime, timedelta
from bson import ObjectId

from config import Config
from dhan_client import DhanAPIClient, DhanAPIError, get_ist_now
from models import (
    get_strategy, update_trade, create_trade, log_alert,
    TRADE_STATUS,
)

logger = logging.getLogger("AlgoX")

# ───── position structure (in-memory cache) ──────────────────
# positions[user_id] = {
#     "trade_id": ObjectId,
#     "security_id": str,
#     "strike": int,
#     "entry_price": float,
#     "exit_price": float | None,
#     "quantity": int,
#     "sl_price": float,          # current stop-loss price
#     "tsl_level": int,            # 0 = initial, 1 = +20, 2 = +40
#     "entry_time": datetime,
#     "status": "OPEN"|"SL_HIT"|...,
#     "is_demo": bool,
#     "exchange_segment": str,
# }


class TradingEngine:
    """Core strategy engine. Thread-safe via ``_lock``."""

    def __init__(self, app, mongo):
        self.app = app
        self.mongo = mongo
        self._lock = threading.RLock()

        # user_id -> DhanAPIClient (None when demo-only)
        self._clients: dict[str, DhanAPIClient | None] = {}

        # user_id -> algo ON/OFF
        self._algo_active: dict[str, bool] = {}

        # user_id -> open position dict
        self._positions: dict[str, dict] = {}

        # user_id -> is_demo bool
        self._demo_mode: dict[str, bool] = {}

        self._scheduler = None

    # ───── user management ───────────────────────────────────
    def register_user(self, user_id: str, client_id: str, access_token: str, is_demo: bool = False):
        """Register (or re-register) a user with the engine."""
        with self._lock:
            self._demo_mode[user_id] = is_demo
            self._algo_active[user_id] = False
            self._clients[user_id] = None if is_demo else DhanAPIClient(client_id, access_token)
            logger.info(f"User {user_id} registered (demo={is_demo})")

    def deregister_user(self, user_id: str):
        """Remove a user from the engine (closes positions, cancels orders)."""
        with self._lock:
            self._exit_position(user_id, "MANUAL_EXIT")
            self._clients.pop(user_id, None)
            self._positions.pop(user_id, None)
            self._algo_active.pop(user_id, None)
            self._demo_mode.pop(user_id, None)
            logger.info(f"User {user_id} deregistered")

    def set_algo_status(self, user_id: str, active: bool):
        """Toggle the algo ON / OFF for a user."""
        with self._lock:
            self._algo_active[user_id] = active
            # Persist to MongoDB
            self.mongo.db.users.update_one(
                {"user_id": user_id},
                {"$set": {"algo_active": active}},
            )
            logger.info(f"User {user_id} algo {'ON' if active else 'OFF'}")
        return active

    def set_demo_mode(self, user_id: str, is_demo: bool):
        """Toggle demo (paper) mode for a user."""
        with self._lock:
            self._demo_mode[user_id] = is_demo
            self._algo_active[user_id] = self._algo_active.get(user_id, False)
            self.mongo.db.users.update_one(
                {"user_id": user_id},
                {"$set": {"is_demo": is_demo}},
            )
            logger.info(f"User {user_id} demo mode {'ON' if is_demo else 'OFF'}")
        return is_demo

    def is_algo_active(self, user_id: str) -> bool:
        with self._lock:
            return self._algo_active.get(user_id, False)

    def get_position(self, user_id: str) -> dict | None:
        with self._lock:
            return self._positions.get(user_id)

    def get_active_positions_count(self) -> int:
        with self._lock:
            return len(self._positions)

    def get_registered_users(self) -> list:
        with self._lock:
            return list(self._clients.keys())

    # ───── entry strategy (9:45 AM) ─────────────────────────
    def execute_entry_strategy(self):
        """Called by the scheduler at 9:45 AM IST.

        Iterates all registered users with algo ON and places a
        BUY order for the ATM NIFTY CE (price 100–140, 1 lot).
        """
        now = get_ist_now()
        logger.info(f"[9:45 Strategy] Starting entry for all active users at {now}")

        with self._lock:
            user_ids = [uid for uid in self._clients if self._algo_active.get(uid, False)]

        for user_id in user_ids:
            try:
                self._try_enter_trade(user_id)
            except Exception as e:
                logger.error(f"Entry failed for {user_id}: {e}")
                log_alert(self.mongo, "ERROR", f"Entry failed for {user_id}: {e}")

    def _try_enter_trade(self, user_id: str):
        """Attempt to enter a single trade for *user_id*."""
        with self._lock:
            is_demo = self._demo_mode.get(user_id, False)
            client = self._clients.get(user_id)

        strategy = get_strategy(self.mongo)
        lot_qty = strategy.get("lot_qty", Config.LOT_QTY)
        min_price = strategy.get("entry_price_min", Config.ENTRY_PRICE_MIN)
        max_price = strategy.get("entry_price_max", Config.ENTRY_PRICE_MAX)
        budget = strategy.get("budget", Config.BUDGET)

        if is_demo:
            # Demo mode still needs a real client for live market data
            user = self.mongo.db.users.find_one({"user_id": user_id})
            if user and user.get("client_id") and user.get("access_token"):
                client = DhanAPIClient(user["client_id"], user["access_token"])
            else:
                logger.warning(f"User {user_id} has no Dhan credentials for demo market data")
                return

        option = client.get_nearest_ce(min_price=min_price, max_price=max_price)
        if not option:
            logger.warning(f"{user_id}: No NIFTY CE in band {min_price}-{max_price}")
            log_alert(self.mongo, "WARNING", f"{user_id}: No CE in price band")
            return

        security_id = option["security_id"]
        strike = option["strike"]
        entry_price = option["last_price"]
        spot = option["spot"]
        expiry = option["expiry"]
        quantity = lot_qty
        cost = entry_price * quantity

        if cost > budget:
            logger.warning(f"User {user_id}: Cost ₹{cost} exceeds budget ₹{budget}")
            return

        with self._lock:
            if user_id in self._positions:
                logger.info(f"User {user_id}: Already has open position, skipping")
                return

        now = get_ist_now()
        today = now.strftime("%Y-%m-%d")

        if is_demo:
            self._enter_demo_trade(user_id, strategy, security_id, strike, entry_price,
                                   spot, expiry, quantity, now, today)
        else:
            self._enter_real_trade(user_id, client, strategy, security_id, strike,
                                   entry_price, spot, expiry, quantity, now, today)

    def _enter_demo_trade(self, user_id, strategy, security_id, strike,
                          entry_price, spot, expiry, quantity, now, today):
        """Simulate a paper-trade entry for demo mode."""
        sl_points = strategy.get("sl_points", Config.SL_POINTS)
        sl_price = entry_price - sl_points
        order_id = f"DEMO-{now.strftime('%Y%m%d%H%M%S')}"

        position = {
            "trade_id": None,
            "order_id": order_id,
            "security_id": str(security_id),
            "exchange_segment": "NSE_FNO",
            "strike": strike,
            "option_type": "CE",
            "entry_price": entry_price,
            "exit_price": None,
            "quantity": quantity,
            "sl_price": sl_price,
            "tsl_level": 0,
            "entry_time": now.isoformat(),
            "status": "OPEN",
            "is_demo": True,
            "spot_price": spot,
            "expiry": expiry,
        }

        trade_data = {
            "user_id": user_id,
            "date": now.strftime("%d %b"),
            "date_iso": today,
            "strike": strike,
            "option_type": "CE",
            "entry_price": entry_price,
            "exit_price": None,
            "quantity": quantity,
            "pnl": None,
            "sl_price": sl_price,
            "tsl_price": None,
            "entry_time": now.isoformat(),
            "exit_time": None,
            "status": "OPEN",
            "order_id": order_id,
            "is_demo": True,
        }
        trade_id = create_trade(self.mongo, trade_data)
        position["trade_id"] = trade_id

        with self._lock:
            self._positions[user_id] = position

        # Deduct from demo capital
        demo_cap = strategy.get("demo_capital", Config.DEMO_CAPITAL)
        self.mongo.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"demo_capital": max(0, demo_cap - entry_price * quantity)}}
        )
        logger.info(f"User {user_id}: DEMO trade. {strike} CE @ {entry_price} SL={sl_price}")

    def _enter_real_trade(self, user_id, client, strategy, security_id, strike,
                          entry_price, spot, expiry, quantity, now, today):
        """Place a REAL buy order via Dhan API."""
        try:
            order_resp = client.place_order(
                security_id=security_id,
                exchange_segment="NSE_FNO",
                transaction_type="BUY",
                quantity=quantity,
                order_type="MARKET",
                product_type="INTRADAY",
                correlation_id=f"algox-{user_id[:8]}-{now.strftime('%H%M%S')}",
            )
            order_id = order_resp.get("orderId", "")
            order_status = order_resp.get("orderStatus", "")

            # Fetch executed price from trade book
            exec_price = entry_price  # fallback
            exec_qty = quantity
            try:
                trades = client.get_trade_book(order_id)
                if trades:
                    last_trade = trades[-1]
                    exec_price = float(last_trade.get("tradedPrice", entry_price))
                    exec_qty = int(last_trade.get("tradedQuantity", quantity))
            except Exception:
                pass  # keep fallback values

            sl_points = strategy.get("sl_points", Config.SL_POINTS)
            sl_price = exec_price - sl_points

            position = {
                "trade_id": None,
                "order_id": order_id,
                "security_id": str(security_id),
                "exchange_segment": "NSE_FNO",
                "strike": strike,
                "option_type": "CE",
                "entry_price": exec_price,
                "exit_price": None,
                "quantity": exec_qty,
                "sl_price": sl_price,
                "tsl_level": 0,
                "entry_time": now.isoformat(),
                "status": "OPEN",
                "is_demo": False,
                "spot_price": spot,
                "expiry": expiry,
            }

            trade_data = {
                "user_id": user_id,
                "date": now.strftime("%d %b"),
                "date_iso": today,
                "strike": strike,
                "option_type": "CE",
                "entry_price": exec_price,
                "exit_price": None,
                "quantity": exec_qty,
                "pnl": None,
                "sl_price": sl_price,
                "tsl_price": None,
                "entry_time": now.isoformat(),
                "exit_time": None,
                "status": "OPEN",
                "order_id": order_id,
                "is_demo": False,
            }
            trade_id = create_trade(self.mongo, trade_data)
            position["trade_id"] = trade_id

            with self._lock:
                self._positions[user_id] = position

            logger.info(f"User {user_id}: REAL trade. Order {order_id} | {strike} CE @ {exec_price} SL={sl_price}")

        except DhanAPIError as e:
            logger.error(f"User {user_id}: Order placement failed: {e}")
            log_alert(self.mongo, "ERROR", f"{user_id}: Order failed: {e}")
        except Exception as e:
            logger.error(f"User {user_id}: Unexpected error in real trade: {e}")
            log_alert(self.mongo, "ERROR", f"{user_id}: Unexpected error: {e}")

    # ───── monitoring (every 30 s) ──────────────────────────
    def monitor_positions(self):
        """Called periodically by the scheduler.
        Checks SL, TSL levels, and time-based exit for all open positions.
        """
        now = get_ist_now()

        with self._lock:
            open_user_ids = [
                uid for uid, pos in self._positions.items()
                if pos["status"] == "OPEN"
            ]

        for user_id in open_user_ids:
            try:
                self._check_and_update_position(user_id, now)
            except Exception as e:
                logger.error(f"Monitor failed for {user_id}: {e}")

    def _check_and_update_position(self, user_id: str, now: datetime):
        """Check SL/TSL/exit conditions for a single open position."""
        with self._lock:
            position = self._positions.get(user_id)
            if not position or position["status"] != "OPEN":
                return
            is_demo = position["is_demo"]

        strategy = get_strategy(self.mongo)
        tsl_levels = strategy.get("tsl_levels", [
            {"trigger": Config.TSL_TRIGGER_1, "sl_offset": Config.TSL_SL_1},
            {"trigger": Config.TSL_TRIGGER_2, "sl_offset": Config.TSL_SL_2},
        ])

        # ── 1. Time-based exit (3:30 PM) ──
        market_close = Config.MARKET_CLOSE_TIME
        if (now.time() >= market_close and now.weekday() < 5):
            logger.info(f"User {user_id}: Market close (3:30 PM) – exiting position")
            self._exit_position(user_id, "TIME_EXIT", now, reason="Market close")
            return

        # ── 2. Get current LTP ──
        current_price = self._get_live_price(user_id, position, is_demo)
        if current_price is None:
            logger.warning(f"User {user_id}: Could not fetch LTP, skipping monitor cycle")
            return

        entry_price = position["entry_price"]
        sl_price = position["sl_price"]
        tsl_level = position.get("tsl_level", 0)

        # ── 3. Check Stop Loss ──
        if current_price <= sl_price:
            logger.info(f"User {user_id}: SL hit! LTP={current_price} <= SL={sl_price}")
            self._exit_position(user_id, "SL_HIT", now, reason=f"SL hit at {current_price}")
            return

        # ── 4. Check TSL levels ──
        profit = current_price - entry_price

        for i, level in enumerate(tsl_levels):
            trigger = level["trigger"]
            sl_offset = level["sl_offset"]

            # Only check the next unreached level
            if i < tsl_level:
                continue

            if profit >= trigger:
                new_sl = entry_price + sl_offset
                if new_sl > sl_price:
                    with self._lock:
                        position["sl_price"] = new_sl
                        position["tsl_level"] = i + 1
                    logger.info(f"User {user_id}: TSL moved to {new_sl} (level {i+1})")

                # If this is the highest TSL level, also exit
                if i == len(tsl_levels) - 1:
                    # At the final TSL level (+40), if price retraces to SL, exit
                    if current_price <= new_sl:
                        self._exit_position(user_id, "TSL_EXIT", now, reason=f"TSL exit at {current_price}")
                        return

    def _get_live_price(self, user_id: str, position: dict, is_demo: bool) -> float | None:
        """Fetch the current LTP for the option in *position*."""
        security_id = position["security_id"]
        exchange_segment = position.get("exchange_segment", "NSE_FNO")

        if is_demo:
            # Demo mode: still fetch live price from Dhan
            user = self.mongo.db.users.find_one({"user_id": user_id})
            if not user or not user.get("client_id") or not user.get("access_token"):
                return None
            client = DhanAPIClient(user["client_id"], user["access_token"])
        else:
            client = self._clients.get(user_id)
            if not client:
                return None

        try:
            ltp_data = client.get_ltp(exchange_segment, [security_id])
            sec_data = ltp_data.get(str(security_id), {})
            return float(sec_data.get("last_price", 0))
        except Exception as e:
            logger.warning(f"LTP fetch failed for {user_id}: {e}")
            return None

    # ───── exit logic ────────────────────────────────────────
    def _exit_position(self, user_id: str, exit_type: str, now: datetime, reason: str = ""):
        """Exit the open position for *user_id*.

        exit_type: SL_HIT, TSL_EXIT, TIME_EXIT, MANUAL_EXIT
        """
        with self._lock:
            position = self._positions.get(user_id)
            if not position:
                return
            # Mark as closing to prevent re-entry
            position["status"] = "CLOSING"

        is_demo = position["is_demo"]
        security_id = position["security_id"]
        exchange_segment = position["exchange_segment"]
        quantity = position["quantity"]
        entry_price = position["entry_price"]
        strategy = get_strategy(self.mongo)

        if is_demo:
            # Simulate exit at current market price
            exit_price = self._get_live_price(user_id, position, True)
            if exit_price is None:
                exit_price = position["entry_price"]  # fallback
            order_id = f"DEMO-EXIT-{now.strftime('%Y%m%d%H%M%S')}"
        else:
            # Place real SELL order
            client = self._clients.get(user_id)
            if not client:
                logger.error(f"User {user_id}: No client for exit")
                return
            try:
                order_resp = client.place_order(
                    security_id=security_id,
                    exchange_segment=exchange_segment,
                    transaction_type="SELL",
                    quantity=quantity,
                    order_type="MARKET",
                    product_type="INTRADAY",
                    correlation_id=f"algox-exit-{user_id[:8]}-{now.strftime('%H%M%S')}",
                )
                order_id = order_resp.get("orderId", "")
                # Try to get executed price
                try:
                    trades = client.get_trade_book(order_id)
                    exit_price = float(trades[-1].get("tradedPrice", 0)) if trades else 0
                except Exception:
                    exit_price = self._get_live_price(user_id, position, False) or 0
            except DhanAPIError as e:
                logger.error(f"User {user_id}: Exit order failed: {e}")
                exit_price = self._get_live_price(user_id, position, False) or 0
                order_id = "FAILED"

        # Calculate P&L
        pnl = (exit_price - entry_price) * quantity

        # Update trade in MongoDB
        trade_id = position["trade_id"]
        if trade_id:
            update_trade(self.mongo, trade_id, **{
                "exit_price": exit_price,
                "pnl": round(pnl, 2),
                "exit_time": now.isoformat(),
                "status": exit_type,
                "sl_hit_price": position["sl_price"],
            })

        # Update demo capital (add back exit proceeds)
        if is_demo:
            user = self.mongo.db.users.find_one({"user_id": user_id})
            if user:
                current_demo = user.get("demo_capital", strategy.get("demo_capital", Config.DEMO_CAPITAL))
                self.mongo.db.users.update_one(
                    {"user_id": user_id},
                    {"$set": {"demo_capital": max(0, current_demo + exit_price * quantity)}}
                )

        # Remove position from memory
        with self._lock:
            if user_id in self._positions and self._positions[user_id]["status"] == "CLOSING":
                del self._positions[user_id]

        logger.info(f"User {user_id}: Position closed. {position['strike']} CE Exit @ {exit_price} P&L={pnl}")
        log_alert(self.mongo, "INFO", f"{user_id}: Trade closed ({exit_type}) P&L={round(pnl, 2)}")

    # ───── exit all at 3:30 PM ───────────────────────────────
    def execute_exit_strategy(self):
        """Force-exit all open positions at market close (3:30 PM)."""
        now = get_ist_now()
        logger.info(f"[Close Strategy] Exiting all open positions at {now}")

        with self._lock:
            open_users = list(self._positions.keys())

        for user_id in open_users:
            self._exit_position(user_id, "TIME_EXIT", now, reason="Market close 3:30 PM")

    # ───── manual exit ───────────────────────────────────────
    def manual_exit(self, user_id: str) -> bool:
        """Manually exit a user's open position (triggered via API)."""
        now = get_ist_now()
        with self._lock:
            has_position = user_id in self._positions and self._positions[user_id]["status"] == "OPEN"
        if has_position:
            self._exit_position(user_id, "MANUAL_EXIT", now, reason="Manual exit")
            return True
        return False

    # ───── scheduler ─────────────────────────────────────────
    def start_scheduler(self):
        """Start APScheduler background jobs."""
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

        # Daily at 9:45 AM IST – entry
        scheduler.add_job(
            func=self.execute_entry_strategy,
            trigger=CronTrigger(hour=9, minute=45, timezone="Asia/Kolkata"),
            id="entry_strategy",
            replace_existing=True,
        )

        # Every 30 seconds – monitor positions
        scheduler.add_job(
            func=self.monitor_positions,
            trigger=CronTrigger(second=0, minute="*/1", timezone="Asia/Kolkata"),
            id="monitor",
            replace_existing=True,
        )

        # Daily at 3:25 PM IST – pre-close check (exit by 3:30)
        scheduler.add_job(
            func=self.execute_exit_strategy,
            trigger=CronTrigger(hour=15, minute=30, timezone="Asia/Kolkata"),
            id="exit_strategy",
            replace_existing=True,
        )

        scheduler.start()
        self._scheduler = scheduler
        logger.info("Trading scheduler started (entry 9:45, monitor 1min, exit 15:30 IST)")

    def shutdown(self):
        """Gracefully shut down the scheduler."""
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            logger.info("Trading scheduler stopped")

    # ───── dashboard data ────────────────────────────────────
    def get_dashboard_data(self, user_id: str) -> dict:
        """Build the dashboard payload for a user."""
        with self._lock:
            position = self._positions.get(user_id)

        user_doc = self.mongo.db.users.find_one({"user_id": user_id})
        if not user_doc:
            return {"error": "User not found"}

        is_demo = user_doc.get("is_demo", False)
        today_pnl = 0.0

        # Compute today's P&L from closed trades today
        today_date = datetime.now().strftime("%d %b")
        today_trades = list(self.mongo.db.trades.find({
            "user_id": user_id,
            "date": today_date,
            "pnl": {"$ne": None},
        }))
        today_pnl = sum(t.get("pnl", 0) for t in today_trades)

        # Open position display
        current_trade = None
        if position and position["status"] == "OPEN":
            live_price = self._get_live_price(user_id, position, is_demo)
            unrealized_pnl = (live_price - position["entry_price"]) * position["quantity"] if live_price else 0
            current_trade = {
                "strike": f"{position['strike']} {position['option_type']}",
                "entry": round(position["entry_price"], 2),
                "sl": round(position["sl_price"], 2),
                "tsl": round(position["sl_price"], 2),
                "qty": position["quantity"],
                "ltp": round(live_price, 2) if live_price else None,
                "unrealized_pnl": round(unrealized_pnl, 2),
                "is_demo": is_demo,
                "entry_time": position["entry_time"],
            }

        return {
            "user_id": user_id,
            "client_id": user_doc.get("client_id"),
            "is_demo": is_demo,
            "algo_active": self._algo_active.get(user_id, False),
            "capital": user_doc.get("demo_capital" if is_demo else "capital", 0),
            "holdings": user_doc.get("holdings", []),
            "today_pnl": round(today_pnl, 2),
            "current_trade": current_trade,
            "positions": self._positions.get(user_id),
        }
