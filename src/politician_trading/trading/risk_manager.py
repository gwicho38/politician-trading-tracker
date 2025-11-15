"""
Risk management for trading operations
"""

from decimal import Decimal
from typing import Optional, Dict, Any

from src.models import Portfolio, Position, TradingSignal
from politician_trading.utils.logger import create_logger

logger = create_logger("risk_manager")


class RiskManager:
    """
    Risk management for trading operations.

    Ensures trades comply with risk limits and position sizing rules.
    """

    def __init__(
        self,
        max_position_size_pct: float = 10.0,  # Max % of portfolio per position
        max_portfolio_risk_pct: float = 2.0,  # Max % portfolio risk per trade
        max_total_exposure_pct: float = 80.0,  # Max % of portfolio invested
        max_positions: int = 20,  # Maximum number of open positions
        min_confidence: float = 0.6,  # Minimum signal confidence
    ):
        """
        Initialize risk manager.

        Args:
            max_position_size_pct: Maximum position size as % of portfolio
            max_portfolio_risk_pct: Maximum risk per trade as % of portfolio
            max_total_exposure_pct: Maximum total exposure as % of portfolio
            max_positions: Maximum number of open positions
            min_confidence: Minimum signal confidence to trade
        """
        self.max_position_size_pct = max_position_size_pct
        self.max_portfolio_risk_pct = max_portfolio_risk_pct
        self.max_total_exposure_pct = max_total_exposure_pct
        self.max_positions = max_positions
        self.min_confidence = min_confidence

        logger.info(
            "Initialized RiskManager",
            metadata={
                "max_position_size_pct": max_position_size_pct,
                "max_portfolio_risk_pct": max_portfolio_risk_pct,
                "max_total_exposure_pct": max_total_exposure_pct,
                "max_positions": max_positions,
                "min_confidence": min_confidence,
            },
        )

    def validate_signal(self, signal: TradingSignal) -> tuple[bool, str]:
        """
        Validate if a signal meets risk criteria.

        Args:
            signal: TradingSignal to validate

        Returns:
            Tuple of (is_valid, reason)
        """
        logger.debug(
            "Validating signal",
            metadata={
                "ticker": signal.ticker,
                "confidence": signal.confidence_score,
                "signal_type": signal.signal_type.value,
            },
        )

        # Check confidence threshold
        if signal.confidence_score < self.min_confidence:
            reason = f"Confidence {signal.confidence_score:.1%} below threshold {self.min_confidence:.1%}"
            logger.info(
                "Signal rejected - low confidence",
                metadata={
                    "ticker": signal.ticker,
                    "confidence": signal.confidence_score,
                    "min_required": self.min_confidence,
                    "reason": reason,
                },
            )
            return False, reason

        # Check if signal has price targets (needed for risk calculation)
        if signal.stop_loss is None and signal.signal_type.value in ["buy", "strong_buy"]:
            logger.warning(
                "Signal missing stop loss",
                metadata={"ticker": signal.ticker, "signal_type": signal.signal_type.value},
            )

        logger.debug("Signal passed validation", metadata={"ticker": signal.ticker})
        return True, "Signal passed validation"

    def calculate_position_size(
        self,
        signal: TradingSignal,
        portfolio: Portfolio,
        current_price: Decimal,
    ) -> Optional[int]:
        """
        Calculate appropriate position size based on risk parameters.

        Args:
            signal: Trading signal
            portfolio: Current portfolio
            current_price: Current price of the asset

        Returns:
            Number of shares to trade, or None if trade should be skipped
        """
        if portfolio.portfolio_value <= 0:
            logger.error("Portfolio value is zero or negative")
            return None

        # Calculate maximum position size based on portfolio percentage
        max_position_value = portfolio.portfolio_value * Decimal(self.max_position_size_pct / 100)

        # Calculate position size based on risk (Kelly criterion simplified)
        if signal.stop_loss and signal.target_price:
            # Risk per share
            risk_per_share = abs(current_price - signal.stop_loss)

            # Max risk amount
            max_risk_amount = portfolio.portfolio_value * Decimal(self.max_portfolio_risk_pct / 100)

            # Position size based on risk
            risk_based_shares = int(max_risk_amount / risk_per_share) if risk_per_share > 0 else 0

            # Position size based on max position value
            value_based_shares = int(max_position_value / current_price)

            # Take the minimum of the two
            shares = min(risk_based_shares, value_based_shares)
        else:
            # If no stop loss, use conservative sizing
            shares = int(max_position_value / current_price)

        # Ensure we can afford it
        cost = shares * current_price
        if cost > portfolio.buying_power:
            shares = int(portfolio.buying_power / current_price)

        # Minimum 1 share
        if shares < 1:
            logger.warning(f"Calculated position size < 1 share for {signal.ticker}")
            return None

        logger.info(
            f"Calculated position size for {signal.ticker}: {shares} shares "
            f"(${float(shares * current_price):.2f})"
        )

        return shares

    def check_portfolio_limits(
        self,
        portfolio: Portfolio,
        positions: list[Position],
        new_trade_value: Decimal,
    ) -> tuple[bool, str]:
        """
        Check if portfolio limits allow for new trade.

        Args:
            portfolio: Current portfolio
            positions: Current open positions
            new_trade_value: Value of new trade to add

        Returns:
            Tuple of (is_allowed, reason)
        """
        # Check max positions
        if len(positions) >= self.max_positions:
            return False, f"Maximum positions limit reached ({self.max_positions})"

        # Check total exposure
        current_exposure = sum(pos.market_value for pos in positions if pos.is_open)
        total_exposure = current_exposure + new_trade_value

        max_exposure = portfolio.portfolio_value * Decimal(self.max_total_exposure_pct / 100)

        if total_exposure > max_exposure:
            exposure_pct = (float(total_exposure) / float(portfolio.portfolio_value)) * 100
            return (
                False,
                f"Total exposure {exposure_pct:.1f}% would exceed limit {self.max_total_exposure_pct}%",
            )

        # Check buying power
        if new_trade_value > portfolio.buying_power:
            return False, f"Insufficient buying power (need ${float(new_trade_value):.2f})"

        return True, "Portfolio limits check passed"

    def should_close_position(
        self,
        position: Position,
        current_price: Decimal,
    ) -> tuple[bool, str]:
        """
        Determine if a position should be closed based on risk parameters.

        Args:
            position: Current position
            current_price: Current price of the asset

        Returns:
            Tuple of (should_close, reason)
        """
        # Check stop loss
        if position.stop_loss:
            if position.side == "long" and current_price <= position.stop_loss:
                return True, f"Stop loss triggered at ${float(current_price):.2f}"
            elif position.side == "short" and current_price >= position.stop_loss:
                return True, f"Stop loss triggered at ${float(current_price):.2f}"

        # Check take profit
        if position.take_profit:
            if position.side == "long" and current_price >= position.take_profit:
                return True, f"Take profit triggered at ${float(current_price):.2f}"
            elif position.side == "short" and current_price <= position.take_profit:
                return True, f"Take profit triggered at ${float(current_price):.2f}"

        # Check for excessive loss (beyond expected stop loss)
        if position.unrealized_pl_pct < -20:  # 20% loss
            return True, f"Excessive loss: {position.unrealized_pl_pct:.1f}%"

        return False, "Position within risk parameters"

    def get_risk_metrics(
        self,
        portfolio: Portfolio,
        positions: list[Position],
    ) -> Dict[str, Any]:
        """
        Calculate current risk metrics for the portfolio.

        Args:
            portfolio: Current portfolio
            positions: Current positions

        Returns:
            Dictionary of risk metrics
        """
        total_exposure = sum(pos.market_value for pos in positions if pos.is_open)
        portfolio_value_float = float(portfolio.portfolio_value) if portfolio.portfolio_value else 0

        exposure_pct = (
            (float(total_exposure) / portfolio_value_float) * 100
            if portfolio_value_float > 0
            else 0
        )

        total_unrealized_pl = sum(pos.unrealized_pl for pos in positions if pos.is_open)
        unrealized_pl_pct = (
            (float(total_unrealized_pl) / portfolio_value_float) * 100
            if portfolio_value_float > 0
            else 0
        )

        # Calculate largest position
        largest_position_value = max(
            [pos.market_value for pos in positions if pos.is_open], default=Decimal(0)
        )
        largest_position_pct = (
            (float(largest_position_value) / portfolio_value_float) * 100
            if portfolio_value_float > 0
            else 0
        )

        # Count winning/losing positions
        winning_positions = sum(1 for pos in positions if pos.is_open and pos.unrealized_pl > 0)
        losing_positions = sum(1 for pos in positions if pos.is_open and pos.unrealized_pl < 0)
        win_rate = (winning_positions / len(positions)) * 100 if positions else 0

        metrics = {
            "total_positions": len(positions),
            "open_positions": sum(1 for pos in positions if pos.is_open),
            "total_exposure": float(total_exposure),
            "exposure_pct": exposure_pct,
            "total_unrealized_pl": float(total_unrealized_pl),
            "unrealized_pl_pct": unrealized_pl_pct,
            "largest_position_value": float(largest_position_value),
            "largest_position_pct": largest_position_pct,
            "winning_positions": winning_positions,
            "losing_positions": losing_positions,
            "win_rate": win_rate,
            "cash_pct": (
                (float(portfolio.cash) / float(portfolio.portfolio_value)) * 100
                if portfolio.portfolio_value > 0
                else 0
            ),
        }

        return metrics

    def get_risk_report(
        self,
        portfolio: Portfolio,
        positions: list[Position],
    ) -> str:
        """
        Generate a human-readable risk report.

        Args:
            portfolio: Current portfolio
            positions: Current positions

        Returns:
            Formatted risk report string
        """
        metrics = self.get_risk_metrics(portfolio, positions)

        report = []
        report.append("=== Risk Report ===")
        report.append(f"Portfolio Value: ${float(portfolio.portfolio_value):,.2f}")
        report.append(f"Cash: ${float(portfolio.cash):,.2f} ({metrics['cash_pct']:.1f}%)")
        report.append(f"Open Positions: {metrics['open_positions']}/{self.max_positions}")
        report.append(
            f"Total Exposure: ${metrics['total_exposure']:,.2f} ({metrics['exposure_pct']:.1f}%)"
        )
        report.append(
            f"Unrealized P&L: ${metrics['total_unrealized_pl']:,.2f} ({metrics['unrealized_pl_pct']:.1f}%)"
        )
        report.append(
            f"Largest Position: ${metrics['largest_position_value']:,.2f} ({metrics['largest_position_pct']:.1f}%)"
        )
        report.append(
            f"Win Rate: {metrics['win_rate']:.1f}% ({metrics['winning_positions']}/{metrics['total_positions']})"
        )
        report.append("")
        report.append("Risk Limits:")
        report.append(f"  Max Position Size: {self.max_position_size_pct}%")
        report.append(f"  Max Risk Per Trade: {self.max_portfolio_risk_pct}%")
        report.append(f"  Max Total Exposure: {self.max_total_exposure_pct}%")
        report.append("")

        # Check for violations
        violations = []
        if metrics["exposure_pct"] > self.max_total_exposure_pct:
            violations.append(
                f"⚠️  EXPOSURE EXCEEDED: {metrics['exposure_pct']:.1f}% > {self.max_total_exposure_pct}%"
            )
        if metrics["largest_position_pct"] > self.max_position_size_pct:
            violations.append(
                f"⚠️  POSITION SIZE EXCEEDED: {metrics['largest_position_pct']:.1f}% > {self.max_position_size_pct}%"
            )
        if metrics["open_positions"] >= self.max_positions:
            violations.append(
                f"⚠️  MAX POSITIONS REACHED: {metrics['open_positions']}/{self.max_positions}"
            )

        if violations:
            report.append("VIOLATIONS:")
            report.extend(violations)
        else:
            report.append("✅ All risk limits within bounds")

        return "\n".join(report)
