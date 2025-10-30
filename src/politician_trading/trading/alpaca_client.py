"""
Alpaca API client for trading operations
"""

from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopOrderRequest,
    StopLimitOrderRequest,
    TrailingStopOrderRequest,
    GetOrdersRequest,
)
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType as AlpacaOrderType
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from src.models import (
    TradingOrder,
    OrderType,
    OrderStatus,
    TradingMode,
    Portfolio,
    Position,
)

logger = logging.getLogger(__name__)


class AlpacaTradingClient:
    """
    Client for interacting with Alpaca API for trading operations.

    Supports both paper trading and live trading.
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        paper: bool = True,
        base_url: str = None,
    ):
        """
        Initialize Alpaca trading client.

        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            paper: Whether to use paper trading (default: True)
            base_url: Optional base URL override
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper = paper
        self.trading_mode = TradingMode.PAPER if paper else TradingMode.LIVE

        # Determine base URL
        if base_url:
            self.base_url = base_url
        elif paper:
            self.base_url = "https://paper-api.alpaca.markets"
        else:
            self.base_url = "https://api.alpaca.markets"

        # Initialize Alpaca clients with explicit URL
        try:
            self.trading_client = TradingClient(
                api_key=api_key,
                secret_key=secret_key,
                paper=paper,
                url_override=self.base_url if paper else None,
            )

            self.data_client = StockHistoricalDataClient(
                api_key=api_key,
                secret_key=secret_key,
            )

            logger.info(f"Initialized Alpaca client in {'paper' if paper else 'live'} mode (URL: {self.base_url})")
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca client: {e}")
            raise

    def get_account(self) -> Dict[str, Any]:
        """
        Get account information.

        Returns:
            Dictionary with account details
        """
        try:
            account = self.trading_client.get_account()
            return {
                "account_id": account.id,
                "status": account.status,
                "cash": Decimal(account.cash),
                "portfolio_value": Decimal(account.portfolio_value),
                "buying_power": Decimal(account.buying_power),
                "equity": Decimal(account.equity),
                "last_equity": Decimal(account.last_equity),
                "long_market_value": Decimal(account.long_market_value),
                "short_market_value": Decimal(account.short_market_value),
                "currency": account.currency,
                "pattern_day_trader": account.pattern_day_trader,
                "trading_blocked": account.trading_blocked,
                "transfers_blocked": account.transfers_blocked,
                "account_blocked": account.account_blocked,
            }
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            raise

    def get_portfolio(self) -> Portfolio:
        """
        Get portfolio information as Portfolio model.

        Returns:
            Portfolio object
        """
        account_info = self.get_account()

        portfolio = Portfolio(
            name=f"Alpaca {'Paper' if self.paper else 'Live'} Account",
            trading_mode=self.trading_mode,
            cash=account_info["cash"],
            portfolio_value=account_info["portfolio_value"],
            buying_power=account_info["buying_power"],
            alpaca_account_id=account_info["account_id"],
            alpaca_account_status=account_info["status"],
            is_active=not account_info["trading_blocked"],
        )

        return portfolio

    def get_positions(self) -> List[Position]:
        """
        Get all open positions.

        Returns:
            List of Position objects
        """
        try:
            alpaca_positions = self.trading_client.get_all_positions()

            positions = []
            for pos in alpaca_positions:
                position = Position(
                    ticker=pos.symbol,
                    asset_name=pos.symbol,
                    quantity=int(pos.qty),
                    side="long" if int(pos.qty) > 0 else "short",
                    avg_entry_price=Decimal(pos.avg_entry_price),
                    total_cost=Decimal(pos.cost_basis),
                    current_price=Decimal(pos.current_price),
                    market_value=Decimal(pos.market_value),
                    unrealized_pl=Decimal(pos.unrealized_pl),
                    unrealized_pl_pct=float(pos.unrealized_plpc) * 100,
                    is_open=True,
                )
                positions.append(position)

            return positions

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            raise

    def place_market_order(
        self,
        ticker: str,
        quantity: int,
        side: str,
        time_in_force: str = "day",
    ) -> TradingOrder:
        """
        Place a market order.

        Args:
            ticker: Stock ticker symbol
            quantity: Number of shares
            side: "buy" or "sell"
            time_in_force: "day", "gtc", "ioc", "fok"

        Returns:
            TradingOrder object
        """
        try:
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            tif = self._parse_time_in_force(time_in_force)

            request = MarketOrderRequest(
                symbol=ticker,
                qty=quantity,
                side=order_side,
                time_in_force=tif,
            )

            alpaca_order = self.trading_client.submit_order(request)

            order = self._convert_alpaca_order(alpaca_order)
            logger.info(f"Placed market {side} order for {quantity} shares of {ticker}")

            return order

        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            raise

    def place_limit_order(
        self,
        ticker: str,
        quantity: int,
        side: str,
        limit_price: Decimal,
        time_in_force: str = "day",
    ) -> TradingOrder:
        """
        Place a limit order.

        Args:
            ticker: Stock ticker symbol
            quantity: Number of shares
            side: "buy" or "sell"
            limit_price: Limit price
            time_in_force: "day", "gtc", "ioc", "fok"

        Returns:
            TradingOrder object
        """
        try:
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            tif = self._parse_time_in_force(time_in_force)

            request = LimitOrderRequest(
                symbol=ticker,
                qty=quantity,
                side=order_side,
                time_in_force=tif,
                limit_price=float(limit_price),
            )

            alpaca_order = self.trading_client.submit_order(request)

            order = self._convert_alpaca_order(alpaca_order)
            logger.info(
                f"Placed limit {side} order for {quantity} shares of {ticker} at ${limit_price}"
            )

            return order

        except Exception as e:
            logger.error(f"Error placing limit order: {e}")
            raise

    def place_stop_order(
        self,
        ticker: str,
        quantity: int,
        side: str,
        stop_price: Decimal,
        time_in_force: str = "day",
    ) -> TradingOrder:
        """
        Place a stop order.

        Args:
            ticker: Stock ticker symbol
            quantity: Number of shares
            side: "buy" or "sell"
            stop_price: Stop price
            time_in_force: "day", "gtc"

        Returns:
            TradingOrder object
        """
        try:
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            tif = self._parse_time_in_force(time_in_force)

            request = StopOrderRequest(
                symbol=ticker,
                qty=quantity,
                side=order_side,
                time_in_force=tif,
                stop_price=float(stop_price),
            )

            alpaca_order = self.trading_client.submit_order(request)

            order = self._convert_alpaca_order(alpaca_order)
            logger.info(f"Placed stop {side} order for {quantity} shares of {ticker} at ${stop_price}")

            return order

        except Exception as e:
            logger.error(f"Error placing stop order: {e}")
            raise

    def place_trailing_stop_order(
        self,
        ticker: str,
        quantity: int,
        side: str,
        trail_percent: float,
        time_in_force: str = "day",
    ) -> TradingOrder:
        """
        Place a trailing stop order.

        Args:
            ticker: Stock ticker symbol
            quantity: Number of shares
            side: "buy" or "sell"
            trail_percent: Trailing stop percentage (e.g., 5.0 for 5%)
            time_in_force: "day", "gtc"

        Returns:
            TradingOrder object
        """
        try:
            order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
            tif = self._parse_time_in_force(time_in_force)

            request = TrailingStopOrderRequest(
                symbol=ticker,
                qty=quantity,
                side=order_side,
                time_in_force=tif,
                trail_percent=trail_percent,
            )

            alpaca_order = self.trading_client.submit_order(request)

            order = self._convert_alpaca_order(alpaca_order)
            logger.info(
                f"Placed trailing stop {side} order for {quantity} shares of {ticker} "
                f"with {trail_percent}% trail"
            )

            return order

        except Exception as e:
            logger.error(f"Error placing trailing stop order: {e}")
            raise

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order.

        Args:
            order_id: Alpaca order ID

        Returns:
            True if successful
        """
        try:
            self.trading_client.cancel_order_by_id(order_id)
            logger.info(f"Canceled order {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error canceling order {order_id}: {e}")
            return False

    def get_order(self, order_id: str) -> TradingOrder:
        """
        Get order by ID.

        Args:
            order_id: Alpaca order ID

        Returns:
            TradingOrder object
        """
        try:
            alpaca_order = self.trading_client.get_order_by_id(order_id)
            return self._convert_alpaca_order(alpaca_order)
        except Exception as e:
            logger.error(f"Error getting order {order_id}: {e}")
            raise

    def get_orders(
        self,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[TradingOrder]:
        """
        Get orders with optional filtering.

        Args:
            status: Filter by status ("open", "closed", "all")
            limit: Maximum number of orders to return

        Returns:
            List of TradingOrder objects
        """
        try:
            request = GetOrdersRequest(
                status=status,
                limit=limit,
            )

            alpaca_orders = self.trading_client.get_orders(filter=request)

            orders = [self._convert_alpaca_order(order) for order in alpaca_orders]
            return orders

        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            raise

    def close_position(self, ticker: str, quantity: Optional[int] = None) -> bool:
        """
        Close a position (sell all or partial).

        Args:
            ticker: Stock ticker symbol
            quantity: Number of shares to sell (None = all)

        Returns:
            True if successful
        """
        try:
            if quantity is None:
                # Close entire position
                self.trading_client.close_position(ticker)
                logger.info(f"Closed entire position in {ticker}")
            else:
                # Close partial position
                current_pos = self.trading_client.get_open_position(ticker)
                side = "sell" if int(current_pos.qty) > 0 else "buy"
                self.place_market_order(ticker, quantity, side)
                logger.info(f"Closed {quantity} shares of {ticker}")

            return True

        except Exception as e:
            logger.error(f"Error closing position in {ticker}: {e}")
            return False

    def _convert_alpaca_order(self, alpaca_order) -> TradingOrder:
        """Convert Alpaca order to TradingOrder model."""
        # Map Alpaca order type to our OrderType
        order_type_map = {
            "market": OrderType.MARKET,
            "limit": OrderType.LIMIT,
            "stop": OrderType.STOP,
            "stop_limit": OrderType.STOP_LIMIT,
            "trailing_stop": OrderType.TRAILING_STOP,
        }

        # Map Alpaca status to our OrderStatus
        status_map = {
            "new": OrderStatus.SUBMITTED,
            "accepted": OrderStatus.SUBMITTED,
            "pending_new": OrderStatus.PENDING,
            "filled": OrderStatus.FILLED,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
            "canceled": OrderStatus.CANCELED,
            "rejected": OrderStatus.REJECTED,
            "expired": OrderStatus.EXPIRED,
        }

        order = TradingOrder(
            ticker=alpaca_order.symbol,
            order_type=order_type_map.get(alpaca_order.type, OrderType.MARKET),
            side=alpaca_order.side.value,
            quantity=int(alpaca_order.qty),
            limit_price=Decimal(alpaca_order.limit_price) if alpaca_order.limit_price else None,
            stop_price=Decimal(alpaca_order.stop_price) if alpaca_order.stop_price else None,
            trailing_percent=float(alpaca_order.trail_percent) if alpaca_order.trail_percent else None,
            status=status_map.get(alpaca_order.status, OrderStatus.PENDING),
            filled_quantity=int(alpaca_order.filled_qty) if alpaca_order.filled_qty else 0,
            filled_avg_price=Decimal(alpaca_order.filled_avg_price) if alpaca_order.filled_avg_price else None,
            trading_mode=self.trading_mode,
            alpaca_order_id=alpaca_order.id,
            alpaca_client_order_id=alpaca_order.client_order_id,
            submitted_at=alpaca_order.submitted_at,
            filled_at=alpaca_order.filled_at,
            canceled_at=alpaca_order.canceled_at,
            expired_at=alpaca_order.expired_at,
        )

        return order

    def _parse_time_in_force(self, tif: str) -> TimeInForce:
        """Parse time in force string to Alpaca enum."""
        tif_map = {
            "day": TimeInForce.DAY,
            "gtc": TimeInForce.GTC,
            "ioc": TimeInForce.IOC,
            "fok": TimeInForce.FOK,
        }
        return tif_map.get(tif.lower(), TimeInForce.DAY)
