"""
Trading strategy engine that executes trades based on politician trading signals
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any
import logging

from politician_trading.trading.alpaca_client import AlpacaTradingClient
from politician_trading.trading.risk_manager import RiskManager
from src.models import (
    TradingSignal,
    TradingOrder,
    Portfolio,
    Position,
    SignalType,
)

logger = logging.getLogger(__name__)


class TradingStrategy:
    """
    Automated trading strategy based on politician trading signals.

    This class orchestrates signal evaluation, risk management, and order execution.
    """

    def __init__(
        self,
        alpaca_client: AlpacaTradingClient,
        risk_manager: RiskManager,
        auto_execute: bool = False,
    ):
        """
        Initialize trading strategy.

        Args:
            alpaca_client: Alpaca trading client
            risk_manager: Risk manager
            auto_execute: Whether to automatically execute trades (default: False for safety)
        """
        self.alpaca_client = alpaca_client
        self.risk_manager = risk_manager
        self.auto_execute = auto_execute

        logger.info(f"Initialized TradingStrategy (auto_execute={auto_execute})")

    def evaluate_signals(
        self,
        signals: List[TradingSignal],
        dry_run: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Evaluate trading signals and determine which trades to make.

        Args:
            signals: List of trading signals
            dry_run: If True, only simulate trades without executing

        Returns:
            List of trade recommendations with execution status
        """
        # Get current portfolio and positions
        portfolio = self.alpaca_client.get_portfolio()
        positions = self.alpaca_client.get_positions()

        # Filter and sort signals
        valid_signals = self._filter_signals(signals, portfolio, positions)

        if not valid_signals:
            logger.info("No valid signals after filtering")
            return []

        logger.info(f"Evaluating {len(valid_signals)} valid signals")

        recommendations = []

        for signal in valid_signals:
            try:
                recommendation = self._evaluate_signal(signal, portfolio, positions, dry_run)
                if recommendation:
                    recommendations.append(recommendation)
            except Exception as e:
                logger.error(f"Error evaluating signal for {signal.ticker}: {e}")

        return recommendations

    def execute_signal(
        self,
        signal: TradingSignal,
        force: bool = False,
    ) -> Optional[TradingOrder]:
        """
        Execute a single trading signal.

        Args:
            signal: Trading signal to execute
            force: Override auto_execute flag

        Returns:
            TradingOrder if executed, None otherwise
        """
        if not self.auto_execute and not force:
            logger.warning("Auto-execute is disabled. Use force=True to override.")
            return None

        # Get current portfolio and positions
        portfolio = self.alpaca_client.get_portfolio()
        positions = self.alpaca_client.get_positions()

        # Validate signal
        is_valid, reason = self.risk_manager.validate_signal(signal)
        if not is_valid:
            logger.warning(f"Signal validation failed for {signal.ticker}: {reason}")
            return None

        # Get current price (from signal or fetch)
        current_price = signal.target_price  # Use target as proxy
        if not current_price:
            logger.error(f"No price information for {signal.ticker}")
            return None

        # Calculate position size
        shares = self.risk_manager.calculate_position_size(signal, portfolio, current_price)
        if not shares:
            logger.warning(f"Could not calculate position size for {signal.ticker}")
            return None

        # Check portfolio limits
        trade_value = Decimal(shares) * current_price
        can_trade, reason = self.risk_manager.check_portfolio_limits(
            portfolio, positions, trade_value
        )
        if not can_trade:
            logger.warning(f"Portfolio limits check failed for {signal.ticker}: {reason}")
            return None

        # Determine order type and side
        if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            side = "buy"
        elif signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            side = "sell"
        else:
            logger.info(f"HOLD signal for {signal.ticker}, no action taken")
            return None

        # Execute order
        try:
            # Use limit order if we have a target price, otherwise market order
            if signal.target_price:
                order = self.alpaca_client.place_limit_order(
                    ticker=signal.ticker,
                    quantity=shares,
                    side=side,
                    limit_price=signal.target_price,
                    time_in_force="day",
                )
            else:
                order = self.alpaca_client.place_market_order(
                    ticker=signal.ticker,
                    quantity=shares,
                    side=side,
                    time_in_force="day",
                )

            order.signal_id = signal.id

            logger.info(
                f"Executed {side} order for {shares} shares of {signal.ticker} "
                f"(Order ID: {order.alpaca_order_id})"
            )

            # Place stop loss order if specified
            if signal.stop_loss and side == "buy":
                self._place_stop_loss(signal.ticker, shares, signal.stop_loss)

            return order

        except Exception as e:
            logger.error(f"Error executing order for {signal.ticker}: {e}")
            return None

    def monitor_positions(self) -> List[Dict[str, Any]]:
        """
        Monitor open positions and check if any should be closed.

        Returns:
            List of position actions taken
        """
        positions = self.alpaca_client.get_positions()

        actions = []

        for position in positions:
            try:
                # Get current price
                current_price = position.current_price

                # Check if position should be closed
                should_close, reason = self.risk_manager.should_close_position(
                    position, current_price
                )

                if should_close:
                    logger.info(f"Closing position in {position.ticker}: {reason}")

                    if self.auto_execute:
                        success = self.alpaca_client.close_position(position.ticker)
                        if success:
                            actions.append(
                                {
                                    "ticker": position.ticker,
                                    "action": "close",
                                    "reason": reason,
                                    "executed": True,
                                }
                            )
                    else:
                        actions.append(
                            {
                                "ticker": position.ticker,
                                "action": "close",
                                "reason": reason,
                                "executed": False,
                                "note": "Auto-execute disabled",
                            }
                        )

            except Exception as e:
                logger.error(f"Error monitoring position {position.ticker}: {e}")

        return actions

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive portfolio summary including risk metrics.

        Returns:
            Dictionary with portfolio summary
        """
        portfolio = self.alpaca_client.get_portfolio()
        positions = self.alpaca_client.get_positions()

        risk_metrics = self.risk_manager.get_risk_metrics(portfolio, positions)

        summary = {
            "portfolio": {
                "value": float(portfolio.portfolio_value),
                "cash": float(portfolio.cash),
                "buying_power": float(portfolio.buying_power),
                "mode": portfolio.trading_mode.value,
            },
            "positions": {
                "total": len(positions),
                "open": sum(1 for p in positions if p.is_open),
                "long": sum(1 for p in positions if p.side == "long" and p.is_open),
                "short": sum(1 for p in positions if p.side == "short" and p.is_open),
            },
            "risk_metrics": risk_metrics,
            "positions_detail": [
                {
                    "ticker": p.ticker,
                    "quantity": p.quantity,
                    "side": p.side,
                    "avg_entry_price": float(p.avg_entry_price),
                    "current_price": float(p.current_price),
                    "market_value": float(p.market_value),
                    "unrealized_pl": float(p.unrealized_pl),
                    "unrealized_pl_pct": p.unrealized_pl_pct,
                }
                for p in positions
                if p.is_open
            ],
        }

        return summary

    def _filter_signals(
        self,
        signals: List[TradingSignal],
        portfolio: Portfolio,
        positions: List[Position],
    ) -> List[TradingSignal]:
        """Filter signals based on basic criteria."""
        valid_signals = []

        # Get existing position tickers
        position_tickers = {p.ticker for p in positions if p.is_open}

        for signal in signals:
            # Skip if we already have a position in this ticker
            if signal.ticker in position_tickers:
                logger.debug(f"Skipping {signal.ticker} - already have position")
                continue

            # Validate signal
            is_valid, reason = self.risk_manager.validate_signal(signal)
            if not is_valid:
                logger.debug(f"Skipping {signal.ticker} - {reason}")
                continue

            # Skip HOLD signals
            if signal.signal_type == SignalType.HOLD:
                continue

            valid_signals.append(signal)

        # Sort by confidence score
        valid_signals.sort(key=lambda s: s.confidence_score, reverse=True)

        return valid_signals

    def _evaluate_signal(
        self,
        signal: TradingSignal,
        portfolio: Portfolio,
        positions: List[Position],
        dry_run: bool,
    ) -> Optional[Dict[str, Any]]:
        """Evaluate a single signal and return recommendation."""
        # Get current price
        current_price = signal.target_price
        if not current_price:
            return None

        # Calculate position size
        shares = self.risk_manager.calculate_position_size(signal, portfolio, current_price)
        if not shares:
            return {
                "ticker": signal.ticker,
                "signal": signal.signal_type.value,
                "confidence": signal.confidence_score,
                "action": "skip",
                "reason": "Position size too small",
            }

        # Check portfolio limits
        trade_value = Decimal(shares) * current_price
        can_trade, reason = self.risk_manager.check_portfolio_limits(
            portfolio, positions, trade_value
        )

        recommendation = {
            "ticker": signal.ticker,
            "signal": signal.signal_type.value,
            "confidence": signal.confidence_score,
            "shares": shares,
            "estimated_cost": float(trade_value),
            "target_price": float(signal.target_price) if signal.target_price else None,
            "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
            "can_trade": can_trade,
            "reason": reason,
        }

        # Execute if conditions are met
        if can_trade and not dry_run and self.auto_execute:
            try:
                order = self.execute_signal(signal, force=True)
                if order:
                    recommendation["executed"] = True
                    recommendation["order_id"] = order.alpaca_order_id
                else:
                    recommendation["executed"] = False
                    recommendation["reason"] = "Execution failed"
            except Exception as e:
                recommendation["executed"] = False
                recommendation["reason"] = str(e)
        else:
            recommendation["executed"] = False

        return recommendation

    def _place_stop_loss(self, ticker: str, quantity: int, stop_price: Decimal):
        """Place a stop loss order for a position."""
        try:
            self.alpaca_client.place_stop_order(
                ticker=ticker,
                quantity=quantity,
                side="sell",
                stop_price=stop_price,
                time_in_force="gtc",
            )
            logger.info(f"Placed stop loss for {ticker} at ${float(stop_price):.2f}")
        except Exception as e:
            logger.error(f"Error placing stop loss for {ticker}: {e}")
