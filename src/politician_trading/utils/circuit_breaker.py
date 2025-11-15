"""
Circuit Breaker pattern implementation for resilient scraping

This module provides a circuit breaker to prevent repeated calls to failing services,
improving system resilience and reducing unnecessary load on target servers.
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit tripped, blocking calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""

    pass


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures

    The circuit breaker has three states:
    - CLOSED: Normal operation, requests go through
    - OPEN: Too many failures, blocking all requests
    - HALF_OPEN: Testing if service recovered

    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before trying half-open state
        expected_exception: Exception type to catch (default: Exception)
        name: Name for this circuit breaker (for logging)
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        name: str = "CircuitBreaker",
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name

        # State tracking
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED

        logger.info(
            f"Circuit breaker '{name}' initialized: "
            f"threshold={failure_threshold}, timeout={recovery_timeout}s"
        )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.state != CircuitState.OPEN:
            return False

        if not self.last_failure_time:
            return True

        time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
        return time_since_failure >= self.recovery_timeout

    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit breaker '{self.name}' recovered - closing circuit")
            self.state = CircuitState.CLOSED

        self.failure_count = 0
        self.last_failure_time = None

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit breaker '{self.name}' test failed - reopening circuit")
            self.state = CircuitState.OPEN
            return

        if self.failure_count >= self.failure_threshold:
            logger.error(
                f"Circuit breaker '{self.name}' opened after {self.failure_count} failures"
            )
            self.state = CircuitState.OPEN

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker

        Args:
            func: Async function to call
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result of function call

        Raises:
            CircuitBreakerError: If circuit is open
            expected_exception: If function fails
        """
        # Check if we should attempt reset
        if self._should_attempt_reset():
            logger.info(f"Circuit breaker '{self.name}' attempting recovery (half-open)")
            self.state = CircuitState.HALF_OPEN

        # Block calls if circuit is open
        if self.state == CircuitState.OPEN:
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is open. "
                f"Service unavailable after {self.failure_count} failures."
            )

        try:
            # Attempt the call
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            logger.error(f"Circuit breaker '{self.name}' recorded failure: {e}")
            raise

    def __call__(self, func: Callable) -> Callable:
        """Decorator interface for circuit breaker"""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)

        return wrapper

    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
            "recovery_timeout": self.recovery_timeout,
        }

    def reset(self):
        """Manually reset the circuit breaker"""
        logger.info(f"Circuit breaker '{self.name}' manually reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None


class CircuitBreakerRegistry:
    """
    Registry to manage multiple circuit breakers for different services
    """

    def __init__(self):
        self.breakers: dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ) -> CircuitBreaker:
        """Get existing circuit breaker or create new one"""
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception,
                name=name,
            )
        return self.breakers[name]

    def get_state_all(self) -> dict[str, dict]:
        """Get state of all circuit breakers"""
        return {name: breaker.get_state() for name, breaker in self.breakers.items()}

    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self.breakers.values():
            breaker.reset()


# Global registry instance
_registry = CircuitBreakerRegistry()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception,
) -> CircuitBreaker:
    """
    Get or create a circuit breaker from the global registry

    Args:
        name: Unique name for the circuit breaker
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: Exception type to catch

    Returns:
        CircuitBreaker instance
    """
    return _registry.get_or_create(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception,
    )


def get_all_circuit_breakers() -> dict[str, dict]:
    """Get state of all circuit breakers in the registry"""
    return _registry.get_state_all()


def reset_all_circuit_breakers():
    """Reset all circuit breakers in the registry"""
    _registry.reset_all()
