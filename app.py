"""
AlgoX – Multi-User Algo Trading Web App (NIFTY 9:45 Strategy)

Flask backend exposing REST APIs for:
  • Dhan account login & token management
  • Dashboard / capital / P&L
  • Option chain & strategy control (ON/OFF, demo)
  • Trade history
  • Multi-user management
"""
import os
import logging
import json
from datetime import datetime, date
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
import pymongo
import mongomock

from config import Config
from dhan_client import DhanAPIClient, DhanAPIError
from trading_engine import TradingEngine, get_ist_now
from models import (
    create_or_update_user, get_user, get_all_users, get_user_count,
    get_trades_by_user, log_alert, get_strategy, seed_demo_trades,
    TRADE_STATUS,
)
from flask.json.provider import DefaultJSONProvider
from bson import ObjectId
from datetime import datetime

# ───── logging ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("AlgoX")


class AlgoXJSONProvider(DefaultJSONProvider):
    """JSON provider that handles MongoDB ObjectId and datetime."""

    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def create_app():
    """Application factory."""
    app = Flask(
        __name__,
        static_folder="frontend/build",
        static_url_path="/assets",
        template_folder="templates",
    )
    app.config.from_object(Config)
    CORS(app)
    app.json = AlgoXJSONProvider(app)

    # ── MongoDB (with mongomock fallback for demos without MongoDB) ──
    # Flask-PyMongo can't be re-initialised after failure, so we create
    # a lightweight wrapper that picks the right driver.
    class _MongoWrapper:
        """Wraps pymongo or mongomock, exposing ``self.db`` like Flask-PyMongo."""
        def __init__(self, config):
            self._config = config
            self._client = None
            self._db = None

        def _init(self):
            if self._client is not None:
                return
            db_name = "algox"
            uri = self._config.get("MONGO_URI", "")
            if uri and "/" in uri:
                db_name = uri.rstrip("/").split("/")[-1].split("?")[0] or db_name
            try:
                import pymongo
                client = pymongo.MongoClient(uri or "mongodb://localhost:27017/algox",
                                             serverSelectionTimeoutMS=3000)
                client.server_info()
                self._client = client
                logger.info("Connected to MongoDB")
            except Exception as e:
                import mongomock
                client = mongomock.MongoClient()
                self._client = client
                logger.warning(f"MongoDB not available ({e}), using in-memory (mongomock)")

            self._db = self._client[db_name]

        @property
        def db(self):
            if self._client is None:
                self._init()
            return self._db

        @property
        def client(self):
            if self._client is None:
                self._init()
            return self._client

    mongo = _MongoWrapper(app.config)
    # Initialise immediately so errors surface early
    mongo._init()

    # ── Trading Engine ──
    trading_engine = TradingEngine(app, mongo)

    # Store on app for route access
    app.mongo = mongo
    app.engine = trading_engine

    # ── Register all routes ──
    register_routes(app, mongo, trading_engine)

    # ── Graceful shutdown ──
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        pass

    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f"Unhandled error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    return app, trading_engine


# ───── route registration ──────────────────────────────────
def register_routes(app, mongo, engine):
    """Register all Flask routes."""

    # ── Health ─────────────────────────────────────────────
    @app.route("/api/health")
    def health():
        return jsonify({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "mode": "demo-ready" if get_user_count(mongo) == 0 else "live",
            "registered_users": engine.get_registered_users(),
        })

    # ── Login / Register ───────────────────────────────────
    @app.route("/api/login", methods=["POST"])
    def login():
        """
        Login endpoint.
        Body: {"client_id": "...", "access_token": "...", "is_demo": false}
        On success the user is registered with the trading engine
        and basic capital / holdings are fetched.
        """
        data = request.get_json()
        client_id = data.get("client_id", "")
        access_token = data.get("access_token", "")
        is_demo = data.get("is_demo", False)

        if not client_id or not access_token:
            return jsonify({"status": "error", "message": "Client ID and Access Token are required"}), 400

        # ── Demo mode: skip Dhan API validation ──
        if is_demo:
            capital = float(Config.DEMO_CAPITAL)
            holdings = []
            positions = []
        else:
            # Validate the token against Dhan by fetching fund limit
            client = DhanAPIClient(client_id, access_token)
            try:
                fund_data = client.get_fund_limit()
            except DhanAPIError as e:
                logger.warning(f"Login validation failed for {client_id}: {e}")
                return jsonify({"status": "error", "message": f"Dhan API error: {e}"}), 401

            capital = float(fund_data.get("availabelBalance", 0))
            holdings = []
            positions = []
            try:
                holdings = client.get_holdings()
            except Exception as e:
                logger.warning(f"Could not fetch holdings for {client_id}: {e}")
            try:
                positions = client.get_positions()
            except Exception as e:
                logger.warning(f"Could not fetch positions for {client_id}: {e}")

        # Store / update user in MongoDB
        user_id = client_id
        create_or_update_user(mongo, user_id, client_id, access_token, is_demo)

        # Update capital
        mongo.db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "capital": capital,
                "last_login": datetime.now(),
                "is_demo": is_demo,
            }}
        )

        # Register with trading engine
        engine.register_user(user_id, client_id, access_token, is_demo)

        mongo.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"holdings": holdings, "positions": positions}}
        )

        # ── Seed demo trade data for new demo users ──
        if is_demo:
            seed_demo_trades(mongo, user_id)

        return jsonify({
            "status": "success",
            "user_id": user_id,
            "client_id": client_id,
            "capital": capital,
            "holdings": holdings,
            "positions": positions,
            "is_demo": is_demo,
            "msg": "Login successful",
        })

    # ── Dashboard ────────────────────────────────────────────
    @app.route("/api/dashboard/<user_id>")
    def dashboard(user_id):
        """Get dashboard data for a user."""
        data = engine.get_dashboard_data(user_id)
        if "error" in data:
            return jsonify(data), 404

        # Also fetch latest fund limit for real mode
        if not data["is_demo"]:
            user = get_user(mongo, user_id)
            if user:
                try:
                    client = DhanAPIClient(user["client_id"], user["access_token"])
                    fund = client.get_fund_limit()
                    holdings = client.get_holdings()
                    data["capital"] = float(fund.get("availabelBalance", 0))
                    data["holdings"] = holdings
                except DhanAPIError:
                    pass

        return jsonify(data)

    # ── Refresh Capital & Holdings ───────────────────────────
    @app.route("/api/refresh/<user_id>")
    def refresh(user_id):
        """Force-refresh capital, holdings, and positions from Dhan API."""
        user = get_user(mongo, user_id)
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        client = DhanAPIClient(user["client_id"], user["access_token"])
        result = {}

        try:
            fund = client.get_fund_limit()
            result["capital"] = float(fund.get("availabelBalance", 0))
        except DhanAPIError as e:
            result["capital"] = user.get("capital", 0)

        try:
            holdings = client.get_holdings()
            result["holdings_count"] = len(holdings)
        except DhanAPIError:
            holdings = []

        try:
            positions = client.get_positions()
            result["positions_count"] = len(positions)
        except DhanAPIError:
            positions = []

        mongo.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"capital": result["capital"], "holdings": holdings, "positions": positions}}
        )

        return jsonify({"status": "success", **result})

    # ── Holdings ─────────────────────────────────────────────
    @app.route("/api/holdings/<user_id>")
    def holdings(user_id):
        user = get_user(mongo, user_id)
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        client = DhanAPIClient(user["client_id"], user["access_token"])
        try:
            holdings = client.get_holdings()
        except DhanAPIError as e:
            return jsonify({"status": "error", "message": str(e)}), 400

        return jsonify({"status": "success", "holdings": holdings})

    # ── Positions ────────────────────────────────────────────
    @app.route("/api/positions/<user_id>")
    def positions(user_id):
        user = get_user(mongo, user_id)
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        client = DhanAPIClient(user["client_id"], user["access_token"])
        try:
            pos = client.get_positions()
        except DhanAPIError as e:
            return jsonify({"status": "error", "message": str(e)}), 400

        return jsonify({"status": "success", "positions": pos})

    # ── Option Chain ─────────────────────────────────────────
    @app.route("/api/optionchain/<user_id>")
    def option_chain(user_id):
        """Get NIFTY option chain for the nearest expiry."""
        user = get_user(mongo, user_id)
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        client = DhanAPIClient(user["client_id"], user["access_token"])
        try:
            expiries = client.get_option_chain_expiry()
            if not expiries:
                return jsonify({"status": "error", "message": "No expiries found"}), 400

            chain = client.get_option_chain(expiries[0])
            return jsonify({
                "status": "success",
                "expiry": expiries[0],
                "spot": chain.get("last_price", 0),
                "option_chain": chain.get("oc", {}),
            })
        except DhanAPIError as e:
            return jsonify({"status": "error", "message": str(e)}), 400

    # ── Nearest CE (for strategy) ────────────────────────────
    @app.route("/api/optionchain/nearest-ce/<user_id>")
    def nearest_ce(user_id):
        """Find the nearest ATM NIFTY CE within price band 100–140."""
        user = get_user(mongo, user_id)
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        client = DhanAPIClient(user["client_id"], user["access_token"])
        try:
            ce = client.get_nearest_ce()
            if ce:
                return jsonify({"status": "success", "option": ce})
            return jsonify({"status": "error", "message": "No suitable CE found in price band 100-140"})
        except DhanAPIError as e:
            return jsonify({"status": "error", "message": str(e)}), 400

    # ── Place Order (manual) ─────────────────────────────────
    @app.route("/api/orders/place", methods=["POST"])
    def place_order():
        """Place a manual order."""
        data = request.get_json()
        user_id = data.get("user_id", "")
        user = get_user(mongo, user_id)
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        client = DhanAPIClient(user["client_id"], user["access_token"])
        try:
            order = client.place_order(
                security_id=data["security_id"],
                exchange_segment=data["exchange_segment"],
                transaction_type=data["transaction_type"],
                quantity=data["quantity"],
                order_type=data.get("order_type", "MARKET"),
                product_type=data.get("product_type", "INTRADAY"),
                price=data.get("price", 0),
                trigger_price=data.get("trigger_price", 0),
                validity=data.get("validity", "DAY"),
                correlation_id=data.get("correlation_id", ""),
            )
            log_alert(mongo, "INFO", f"{user_id}: Order placed {order}")
            return jsonify({"status": "success", "order": order})
        except DhanAPIError as e:
            log_alert(mongo, "ERROR", f"{user_id}: Order failed: {e}")
            return jsonify({"status": "error", "message": str(e)}), 400

    # ── Strategy: Toggle ON / OFF ────────────────────────────
    @app.route("/api/strategy/toggle", methods=["POST"])
    def toggle_strategy():
        """Toggle algo ON/OFF for a user.
        Body: {"user_id": "...", "active": true}
        """
        data = request.get_json()
        user_id = data.get("user_id", "")
        active = data.get("active", False)

        user = get_user(mongo, user_id)
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        engine.set_algo_status(user_id, active)
        status = "ON" if active else "OFF"
        log_alert(mongo, "INFO", f"{user_id}: Algo switched {status}")
        return jsonify({
            "status": "success",
            "algo_active": engine.is_algo_active(user_id),
            "message": f"Algo {status}",
        })

    # ── Demo Toggle ──────────────────────────────────────────
    @app.route("/api/demo/toggle", methods=["POST"])
    def toggle_demo():
        """Toggle demo (paper) mode.
        Body: {"user_id": "...", "is_demo": true}
        """
        data = request.get_json()
        user_id = data.get("user_id", "")
        is_demo = data.get("is_demo", False)

        user = get_user(mongo, user_id)
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        engine.set_demo_mode(user_id, is_demo)
        if is_demo:
            mongo.db.users.update_one(
                {"user_id": user_id},
                {"$set": {"demo_capital": Config.DEMO_CAPITAL}},
            )
        mode = "DEMO (paper trading)" if is_demo else "REAL (live Dhan account)"
        log_alert(mongo, "INFO", f"{user_id}: Mode switched to {mode}")
        return jsonify({
            "status": "success",
            "is_demo": is_demo,
            "message": f"Mode set to {mode}",
        })

    # ── Manual Entry / Exit ───────────────────────────────────
    @app.route("/api/strategy/entry", methods=["POST"])
    def manual_entry():
        """Trigger the 9:45 entry strategy manually for a user."""
        data = request.get_json()
        user_id = data.get("user_id", "")

        if user_id not in engine.get_registered_users():
            return jsonify({"status": "error", "message": "User not registered"}), 404
        if not engine.is_algo_active(user_id):
            return jsonify({"status": "error", "message": "Algo is OFF"}), 400

        engine._try_enter_trade(user_id)
        pos = engine.get_position(user_id)
        if pos:
            return jsonify({"status": "success", "position": pos})
        return jsonify({"status": "error", "message": "Entry failed – no suitable CE found"})

    @app.route("/api/strategy/exit", methods=["POST"])
    def manual_exit():
        """Manually exit an open position."""
        data = request.get_json()
        user_id = data.get("user_id", "")
        result = engine.manual_exit(user_id)
        return jsonify({
            "status": "success" if result else "error",
            "message": "Position closed" if result else "No open position",
        })

    @app.route("/api/position/<user_id>")
    def current_position(user_id):
        pos = engine.get_position(user_id)
        if pos:
            return jsonify({"status": "success", "position": pos})
        return jsonify({"status": "success", "position": None, "message": "No open position"})

    @app.route("/api/orders/<user_id>")
    def orders(user_id):
        user = get_user(mongo, user_id)
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        client = DhanAPIClient(user["client_id"], user["access_token"])
        try:
            order_list = client.get_order_list()
            return jsonify({"status": "success", "orders": order_list})
        except DhanAPIError as e:
            return jsonify({"status": "error", "message": str(e)}), 400

    # ── Trade History ────────────────────────────────────────
    @app.route("/api/trade-history/<user_id>")
    def trade_history(user_id):
        trades = get_trades_by_user(mongo, user_id, limit=200)
        result = []
        for t in trades:
            result.append({
                "id": str(t["_id"]),
                "date": t.get("date", ""),
                "strike": t.get("strike", 0),
                "option_type": t.get("option_type", "CE"),
                "entry": round(t.get("entry_price", 0), 2),
                "exit": round(t.get("exit_price", 0), 2) if t.get("exit_price") else None,
                "qty": t.get("quantity", 0),
                "pnl": round(t.get("pnl", 0), 2) if t.get("pnl") is not None else None,
                "sl_price": round(t.get("sl_price", 0), 2),
                "entry_time": t.get("entry_time", ""),
                "exit_time": t.get("exit_time", "") if t.get("exit_time") else "",
                "status": t.get("status", ""),
                "is_demo": t.get("is_demo", False),
            })
        return jsonify({"status": "success", "trades": result})

    # ── Users Count ────────────────────────────────────────
    @app.route("/api/users/count")
    def user_count():
        return jsonify({"count": get_user_count(mongo)})

    # ── All Users (admin) ───────────────────────────────────
    @app.route("/api/users")
    def all_users():
        users = get_all_users(mongo)
        result = []
        for u in users:
            result.append({
                "user_id": u.get("user_id"),
                "client_id": u.get("client_id"),
                "is_demo": u.get("is_demo", False),
                "algo_active": engine.is_algo_active(u.get("user_id")),
                "capital": u.get("capital", 0),
                "demo_capital": u.get("demo_capital", 0),
                "last_login": u.get("last_login"),
                "created_at": u.get("created_at"),
            })
        return jsonify({"status": "success", "users": result, "count": len(result)})

    # ── Alerts ─────────────────────────────────────────────
    @app.route("/api/alerts")
    def alerts():
        cursor = mongo.db.alerts.find({}).sort("timestamp", -1).limit(50)
        result = [
            {
                "level": doc.get("level"),
                "message": doc.get("message"),
                "timestamp": doc.get("timestamp"),
            }
            for doc in cursor
        ]
        return jsonify({"status": "success", "alerts": result})

    # ── Strategy Config ────────────────────────────────────
    @app.route("/api/strategy/config", methods=["GET", "POST"])
    def strategy_config():
        if request.method == "GET":
            return jsonify({"status": "success", "config": get_strategy(mongo)})

        data = request.get_json()
        allowed = [
            "lot_qty", "budget", "entry_price_min", "entry_price_max",
            "sl_points", "tsl_levels", "market_open", "market_close",
        ]
        updates = {k: v for k, v in data.items() if k in allowed}
        if not updates:
            return jsonify({"status": "error", "message": "No valid fields"}), 400

        from models import update_strategy
        update_strategy(mongo, **updates)
        log_alert(mongo, "INFO", f"Strategy config updated: {list(updates.keys())}")
        return jsonify({"status": "success", "config": get_strategy(mongo)})

    # ── Serve React app ──────────────────────────────────────
    @app.route("/app")
    def react_app():
        build_dir = os.path.join(os.path.dirname(__file__), "frontend", "build")
        if os.path.exists(os.path.join(build_dir, "index.html")):
            return send_from_directory(build_dir, "index.html")
        return render_template("index.html")

    @app.route("/app/<path:subpath>")
    def react_app_static(subpath):
        build_dir = os.path.join(os.path.dirname(__file__), "frontend", "build")
        if os.path.exists(build_dir):
            return send_from_directory(build_dir, subpath)
        return ("Not found", 404)

    @app.route("/<path:catch_all>")
    def catch_all(catch_all):
        if catch_all.startswith("api/"):
            return jsonify({"status": "error", "message": "Not found"}), 404
        build_dir = os.path.join(os.path.dirname(__file__), "frontend", "build")
        if os.path.exists(os.path.join(build_dir, "index.html")):
            return send_from_directory(build_dir, "index.html")
        return render_template("index.html")

    # ── Ensure default strategy exists ────────────────────────
    @app.before_request
    def ensure_strategy():
        mongo.db.strategy.update_one(
            {}, {"$setOnInsert": get_strategy(mongo)}, upsert=True
        )


# ───── main entry point ──────────────────────────────────────
if __name__ == "__main__":
    app, engine = create_app()
    engine.start_scheduler()
    logger.info(f"Starting AlgoX server on port {Config.PORT}")
    logger.info(f"Dashboard: http://localhost:{Config.PORT}/app")
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG, use_reloader=False)