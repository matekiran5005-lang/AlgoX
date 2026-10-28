"""
DhanHQ API Client – thin wrapper around the Dhan v2 REST API.

Provides methods for:
  • Authentication / client validation
  • Funds & margin retrieval
  • Holdings & positions
  • Option chain (NIFTY)
  • Market data (LTP, OHLC, quotes)
  • Order placement, cancellation, status
"""
import requests
from datetime import datetime, timezone


class DhanAPIError(Exception):
    """Raised when the Dhan API returns an error."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(message)


class DhanAPIClient:
    """Synchronous Dhan v2 REST API client.

    Parameters
    ----------
    client_id : str
        Dhan assigned client id (e.g. ``"1000000001"``).
    access_token : str
        JWT access token from the Dhan app / OAuth flow.
    """

    # NIFTY 50 constants
    NIFTY_UNDERLYING_SCRIP = 13
    NIFTY_SEGMENT = "IDX_I"
    OPTION_EXCHANGE_SEGMENT = "NSE_FNO"

    def __init__(self, client_id: str, access_token: str):
        self.client_id = client_id
        self.access_token = access_token
        self.base_url = "https://api.dhan.co/v2"
        self.headers = {
            "Content-Type": "application/json",
            "access-token": access_token,
            "client-id": client_id,
        }

    # ───── helpers ────────────────────────────────────────────
    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self.base_url}{path}"
        kwargs.setdefault("headers", self.headers)
        kwargs.setdefault("timeout", 30)
        resp = requests.request(method, url, **kwargs)
        data = resp.json()

        if resp.status_code != 200 or data.get("status") == "error":
            msg = data.get("message", "Unknown Dhan API error")
            raise DhanAPIError(resp.status_code, msg)

        return data

    # ───── authentication / validation ─────────────────────
    def validate(self) -> dict:
        """Hit ``/fundlimit`` to verify the token is valid and return capital."""
        return self._request("GET", "/fundlimit")

    @property
    def is_authenticated(self) -> bool:
        """Quick check whether the token can be used (best-effort)."""
        try:
            self.validate()
            return True
        except DhanAPIError:
            return False

    # ───── funds & margin ────────────────────────────────────
    def get_fund_limit(self) -> dict:
        """Retrieve available fund limits and margin utilisation.

        Returns a dict with:
            dhanClientId, availabelBalance, sodLimit,
            collateralAmount, receiveableAmount, utilisedAmount,
            blockedPayoutAmount, withdrawableBalance
        """
        return self._request("GET", "/fundlimit")

    def get_holdings(self) -> list:
        """Retrieve all holdings in the demat account."""
        data = self._request("GET", "/holdings")
        return data.get("data", [])

    def get_positions(self) -> list:
        """Retrieve all open positions for the day."""
        data = self._request("GET", "/positions")
        return data.get("data", [])

    # ───── option chain ──────────────────────────────────────
    def get_option_chain_expiry(self) -> list:
        """Get the list of active expiries for NIFTY options.

        Returns
        -------
        list[str]
            Expiry dates in ``YYYY-MM-DD`` format, nearest first.
        """
        payload = {
            "UnderlyingScrip": self.NIFTY_UNDERLYING_SCRIP,
            "UnderlyingSeg": self.NIFTY_SEGMENT,
        }
        data = self._request("POST", "/optionchain/expirylist", json=payload)
        return data.get("data", [])

    def get_option_chain(self, expiry: str) -> dict:
        """Get the full NIFTY option chain for *expiry*.

        Returns a dict with:
            last_price  – spot NIFTY LTP
            oc          – {strike_str: {"ce": {...}, "pe": {...}}}
        """
        payload = {
            "UnderlyingScrip": self.NIFTY_UNDERLYING_SCRIP,
            "UnderlyingSeg": self.NIFTY_SEGMENT,
            "Expiry": expiry,
        }
        data = self._request("POST", "/optionchain", json=payload)
        return data.get("data", {})

    def get_nearest_ce(self, min_price: float = 100, max_price: float = 140) -> dict | None:
        """Find the nearest-to-money NIFTY CE option whose last price
        falls within *[min_price, max_price]*.

        Returns ``{"strike", "security_id", "last_price", "spot", "expiry"}``
        or ``None``.
        """
        expiries = self.get_option_chain_expiry()
        if not expiries:
            return None

        expiry = expiries[0]  # nearest expiry
        chain = self.get_option_chain(expiry)
        spot = chain.get("last_price", 0)
        oc = chain.get("oc", {})

        # Find the strike nearest to spot (multiples of 50)
        nearest_strike = round(spot / 50) * 50
        strikes = sorted([float(s) for s in oc.keys()])
        search_order = sorted(strikes, key=lambda s: abs(s - nearest_strike))

        for strike in search_order:
            key_variants = [str(int(strike)), f"{int(strike)}.0", f"{int(strike)}.000000"]
            for key in key_variants:
                if key in oc and "ce" in oc[key]:
                    ce = oc[key]["ce"]
                    last_price = ce.get("last_price", 0)
                    security_id = ce.get("security_id")
                    if min_price <= last_price <= max_price and security_id:
                        return {
                            "strike": int(strike),
                            "security_id": security_id,
                            "last_price": last_price,
                            "spot": spot,
                            "expiry": expiry,
                        }
        return None

    # ───── market data ───────────────────────────────────────
    def get_ltp(self, exchange_segment: str, security_ids: list) -> dict:
        """Get last traded price for securities in *exchange_segment*.

        Parameters
        ----------
        exchange_segment : str
            e.g. ``"NSE_EQ"``, ``"NSE_FNO"``.
        security_ids : list
            List of security ids (ints or strs).

        Returns ``{security_id: {"last_price": float}}``.
        """
        payload = {exchange_segment: [int(sid) for sid in security_ids]}
        data = self._request("POST", "/marketfeed/ltp", json=payload)
        return data.get("data", {}).get(exchange_segment, {})

    def get_quote(self, exchange_segment: str, security_ids: list) -> dict:
        """Get full quote data (OHLC, depth, OI) for instruments."""
        payload = {exchange_segment: [int(sid) for sid in security_ids]}
        data = self._request("POST", "/marketfeed/quote", json=payload)
        return data.get("data", {}).get(exchange_segment, {})

    def get_ohlc(self, exchange_segment: str, security_ids: list) -> dict:
        """Get OHLC data for instruments."""
        payload = {exchange_segment: [int(sid) for sid in security_ids]}
        data = self._request("POST", "/marketfeed/ohlc", json=payload)
        return data.get("data", {}).get(exchange_segment, {})

    # ───── orders ────────────────────────────────────────────
    def place_order(
        self,
        security_id,
        exchange_segment: str,
        transaction_type: str,
        quantity: int,
        order_type: str = "MARKET",
        product_type: str = "INTRADAY",
        price: float = 0,
        trigger_price: float = 0,
        validity: str = "DAY",
        correlation_id: str = "",
    ) -> dict:
        """Place a new order.

        Parameters
        ----------
        security_id : str | int
            Exchange security id of the instrument.
        exchange_segment : str
            e.g. ``"NSE_EQ"``, ``"NSE_FNO"``.
        transaction_type : str
            ``"BUY"`` or ``"SELL"``.
        quantity : int
            Number of shares / contracts.
        order_type : str
            ``"MARKET"``, ``"LIMIT"``, ``"STOP_LOSS"``, ``"STOP_LOSS_MARKET"``.
        product_type : str
            ``"CNC"``, ``"INTRADAY"``, ``"MARGIN"``.
        price : float
            Order price (0 for market).
        trigger_price : float
            Trigger price for SL orders.
        validity : str
            ``"DAY"``, ``"IOC"``.
        correlation_id : str
            Custom id for tracking (max 30 chars).

        Returns ``{"orderId": str, "orderStatus": str}``.
        """
        payload = {
            "dhanClientId": self.client_id,
            "correlationId": correlation_id or f"algox-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "transactionType": transaction_type,
            "exchangeSegment": exchange_segment,
            "productType": product_type,
            "orderType": order_type,
            "validity": validity,
            "securityId": str(security_id),
            "quantity": str(quantity),
            "disclosedQuantity": "",
            "price": str(price) if price else "",
            "triggerPrice": str(trigger_price) if trigger_price else "",
            "afterMarketOrder": False,
            "amoTime": "",
        }
        return self._request("POST", "/orders", json=payload)

    def place_stop_loss_order(
        self,
        security_id,
        exchange_segment: str,
        quantity: int,
        trigger_price: float,
        correlation_id: str = "",
    ) -> dict:
        """Place a stop-loss market (SELL) order to exit a position."""
        payload = {
            "dhanClientId": self.client_id,
            "correlationId": correlation_id or f"algox-sl-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "transactionType": "SELL",
            "exchangeSegment": exchange_segment,
            "productType": "INTRADAY",
            "orderType": "STOP_LOSS_MARKET",
            "validity": "DAY",
            "securityId": str(security_id),
            "quantity": str(quantity),
            "disclosedQuantity": "",
            "price": "",
            "triggerPrice": str(trigger_price),
            "afterMarketOrder": False,
            "amoTime": "",
        }
        return self._request("POST", "/orders", json=payload)

    def cancel_order(self, order_id: str) -> dict:
        """Cancel a pending order by order id."""
        return self._request("DELETE", f"/orders/{order_id}")

    def get_order_by_id(self, order_id: str) -> dict:
        """Retrieve status of a specific order."""
        return self._request("GET", f"/orders/{order_id}")

    def get_order_list(self) -> list:
        """Retrieve all orders for the current trading day."""
        data = self._request("GET", "/orders")
        return data.get("data", [])

    def get_trade_book(self, order_id: str = None) -> list:
        """Retrieve trade book. If *order_id* is given, return trades for that order."""
        path = f"/trades/{order_id}" if order_id else "/trades"
        data = self._request("GET", path)
        return data.get("data", [])


# ───── convenience: IST timezone ─────────────────────────────
def get_ist_now() -> datetime:
    """Return current time in IST (UTC+5:30)."""
    from datetime import timedelta

    utc = datetime.now(timezone.utc)
    ist = utc + timedelta(hours=5, minutes=30)
    return ist
