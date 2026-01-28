"""
Tests for SignalLambdaSandbox (app/services/sandbox.py).

Security-focused unit tests ensuring the sandbox properly restricts
dangerous operations while allowing legitimate signal transformations.
"""

import pytest
from app.services.sandbox import (
    SignalLambdaSandbox,
    apply_lambda_to_signals,
    LambdaValidationError,
    LambdaExecutionError,
    CapturedPrint,
    ExecutionTrace,
)


# =============================================================================
# CapturedPrint Tests
# =============================================================================

class TestCapturedPrint:
    """Tests for print capture functionality."""

    def test_captures_simple_output(self):
        """CapturedPrint captures basic print output."""
        capture = CapturedPrint()
        capture("hello", "world")
        assert capture.get_output() == ["hello world"]

    def test_respects_max_lines(self):
        """CapturedPrint respects line limit."""
        capture = CapturedPrint(max_lines=3)
        for i in range(10):
            capture(f"line {i}")
        assert len(capture.get_output()) == 3

    def test_truncates_long_lines(self):
        """CapturedPrint truncates lines exceeding max length."""
        capture = CapturedPrint(max_chars_per_line=10)
        capture("a" * 100)
        output = capture.get_output()[0]
        assert len(output) < 100
        assert "truncated" in output


# =============================================================================
# SignalLambdaSandbox Validation Tests
# =============================================================================

class TestSandboxValidation:
    """Tests for code validation before execution."""

    @pytest.fixture
    def sandbox(self):
        return SignalLambdaSandbox()

    def test_rejects_empty_code(self, sandbox):
        """Validation rejects empty code."""
        with pytest.raises(LambdaValidationError, match="Empty code"):
            sandbox.validate_code("")

    def test_rejects_whitespace_only(self, sandbox):
        """Validation rejects whitespace-only code."""
        with pytest.raises(LambdaValidationError, match="Empty code"):
            sandbox.validate_code("   \n\t  ")

    def test_rejects_oversized_code(self, sandbox):
        """Validation rejects code exceeding size limit."""
        huge_code = "x = 1\n" * 10000
        with pytest.raises(LambdaValidationError, match="exceeds maximum size"):
            sandbox.validate_code(huge_code)

    def test_rejects_syntax_errors(self, sandbox):
        """Validation rejects code with syntax errors."""
        with pytest.raises(LambdaValidationError, match="Syntax error"):
            sandbox.validate_code("if True print('x')")

    def test_accepts_valid_code(self, sandbox):
        """Validation accepts valid safe code."""
        sandbox.validate_code("result = signal")  # Should not raise


# =============================================================================
# Forbidden Operations Tests
# =============================================================================

class TestForbiddenOperations:
    """Tests ensuring dangerous operations are blocked."""

    @pytest.fixture
    def sandbox(self):
        return SignalLambdaSandbox()

    # --- Import statements ---

    def test_rejects_import(self, sandbox):
        """Validation rejects import statements."""
        with pytest.raises(LambdaValidationError, match="Forbidden operation"):
            sandbox.validate_code("import os")

    def test_rejects_from_import(self, sandbox):
        """Validation rejects from...import statements."""
        with pytest.raises(LambdaValidationError, match="Forbidden operation"):
            sandbox.validate_code("from os import system")

    # --- Dangerous builtins ---

    def test_rejects_eval(self, sandbox):
        """Validation rejects eval calls."""
        with pytest.raises(LambdaValidationError, match="Forbidden function"):
            sandbox.validate_code("eval('1+1')")

    def test_rejects_exec(self, sandbox):
        """Validation rejects exec calls."""
        with pytest.raises(LambdaValidationError, match="Forbidden function"):
            sandbox.validate_code("exec('print(1)')")

    def test_rejects_compile(self, sandbox):
        """Validation rejects compile calls."""
        with pytest.raises(LambdaValidationError, match="Forbidden function"):
            sandbox.validate_code("compile('x=1', '', 'exec')")

    def test_rejects_open(self, sandbox):
        """Validation rejects file open calls."""
        with pytest.raises(LambdaValidationError, match="Forbidden function"):
            sandbox.validate_code("open('/etc/passwd')")

    def test_rejects___import__(self, sandbox):
        """Validation rejects __import__ calls."""
        with pytest.raises(LambdaValidationError, match="Forbidden function"):
            sandbox.validate_code("__import__('os')")

    def test_rejects_getattr(self, sandbox):
        """Validation rejects getattr calls (attribute access bypass)."""
        with pytest.raises(LambdaValidationError, match="Forbidden function"):
            sandbox.validate_code("getattr(signal, '__class__')")

    # --- Dunder attribute access ---

    def test_rejects_class_access(self, sandbox):
        """Validation rejects __class__ access."""
        with pytest.raises(LambdaValidationError, match="Forbidden.*__class__"):
            sandbox.validate_code("signal.__class__")

    def test_rejects_globals_access(self, sandbox):
        """Validation rejects __globals__ access."""
        with pytest.raises(LambdaValidationError, match="Forbidden.*__globals__"):
            sandbox.validate_code("(lambda: None).__globals__")

    def test_rejects_builtins_access(self, sandbox):
        """Validation rejects __builtins__ access."""
        with pytest.raises(LambdaValidationError, match="Forbidden.*__builtins__"):
            sandbox.validate_code("x.__builtins__")

    def test_rejects_subclasses_access(self, sandbox):
        """Validation rejects __subclasses__ access."""
        with pytest.raises(LambdaValidationError, match="Forbidden.*__subclasses__"):
            sandbox.validate_code("().__class__.__subclasses__()")

    # --- Async operations ---

    def test_rejects_async_function(self, sandbox):
        """Validation rejects async function definitions."""
        with pytest.raises(LambdaValidationError, match="Forbidden operation"):
            sandbox.validate_code("async def f(): pass")

    def test_rejects_await(self, sandbox):
        """Validation rejects await expressions."""
        with pytest.raises(LambdaValidationError, match="Forbidden operation"):
            sandbox.validate_code("await something")


# =============================================================================
# Sandbox Execution Tests
# =============================================================================

class TestSandboxExecution:
    """Tests for safe code execution."""

    @pytest.fixture
    def sandbox(self):
        return SignalLambdaSandbox()

    @pytest.fixture
    def sample_signal(self):
        return {
            "ticker": "AAPL",
            "confidence_score": 0.8,
            "signal_type": "buy",
            "signal_strength": "strong",
        }

    def test_executes_simple_passthrough(self, sandbox, sample_signal):
        """Sandbox executes simple passthrough code."""
        compiled = sandbox.compile_lambda("result = signal")
        result = sandbox.execute(compiled, sample_signal)
        assert result["ticker"] == "AAPL"
        assert result["confidence_score"] == 0.8

    def test_modifies_signal_values(self, sandbox, sample_signal):
        """Sandbox allows signal modification."""
        code = """
signal['confidence_score'] = 0.9
result = signal
"""
        compiled = sandbox.compile_lambda(code)
        result = sandbox.execute(compiled, sample_signal)
        assert result["confidence_score"] == 0.9

    def test_uses_math_functions(self, sandbox, sample_signal):
        """Sandbox provides safe math functions."""
        code = """
signal['confidence_score'] = math.sqrt(signal['confidence_score'])
result = signal
"""
        compiled = sandbox.compile_lambda(code)
        result = sandbox.execute(compiled, sample_signal)
        assert abs(result["confidence_score"] - 0.894) < 0.01

    def test_captures_print_output(self, sandbox, sample_signal):
        """Sandbox captures print statements."""
        code = """
print("Debug:", signal['ticker'])
result = signal
"""
        captured = CapturedPrint()
        compiled = sandbox.compile_lambda(code)
        sandbox.execute(compiled, sample_signal, captured)
        assert "Debug: AAPL" in captured.get_output()[0]

    def test_timeout_on_infinite_loop(self, sandbox, sample_signal):
        """Sandbox times out on infinite loops."""
        code = """
while True:
    pass
result = signal
"""
        compiled = sandbox.compile_lambda(code)
        with pytest.raises(LambdaExecutionError, match="timed out"):
            sandbox.execute(compiled, sample_signal)

    def test_requires_result_dict(self, sandbox, sample_signal):
        """Sandbox requires result to be a dict."""
        code = "result = 'not a dict'"
        compiled = sandbox.compile_lambda(code)
        with pytest.raises(LambdaExecutionError, match="must return a dict"):
            sandbox.execute(compiled, sample_signal)

    def test_requires_ticker_field(self, sandbox, sample_signal):
        """Sandbox requires ticker field in result."""
        code = "result = {'foo': 'bar'}"
        compiled = sandbox.compile_lambda(code)
        with pytest.raises(LambdaExecutionError, match="missing required 'ticker'"):
            sandbox.execute(compiled, sample_signal)

    def test_original_signal_not_modified(self, sandbox, sample_signal):
        """Sandbox does not modify the original signal."""
        original_score = sample_signal["confidence_score"]
        code = """
signal['confidence_score'] = 0.1
result = signal
"""
        compiled = sandbox.compile_lambda(code)
        sandbox.execute(compiled, sample_signal)
        # Original should be unchanged
        assert sample_signal["confidence_score"] == original_score


# =============================================================================
# apply_lambda_to_signals Tests
# =============================================================================

class TestApplyLambdaToSignals:
    """Tests for the high-level apply function."""

    def test_applies_to_multiple_signals(self):
        """apply_lambda_to_signals processes multiple signals."""
        signals = [
            {"ticker": "AAPL", "confidence_score": 0.8, "signal_type": "buy"},
            {"ticker": "GOOG", "confidence_score": 0.6, "signal_type": "hold"},
        ]
        code = """
signal['confidence_score'] = signal['confidence_score'] + 0.1
result = signal
"""
        results, trace = apply_lambda_to_signals(signals, code)

        assert len(results) == 2
        assert results[0]["confidence_score"] == 0.9
        assert results[1]["confidence_score"] == 0.7
        assert trace.signals_processed == 2

    def test_tracks_modifications(self):
        """apply_lambda_to_signals tracks modified signals."""
        signals = [
            {"ticker": "AAPL", "confidence_score": 0.8, "signal_type": "buy"},
            {"ticker": "GOOG", "confidence_score": 0.6, "signal_type": "hold"},
        ]
        code = """
if signal['confidence_score'] > 0.7:
    signal['confidence_score'] = 0.99
result = signal
"""
        results, trace = apply_lambda_to_signals(signals, code)

        assert trace.signals_modified == 1  # Only AAPL modified

    def test_continues_on_single_error(self):
        """apply_lambda_to_signals continues after single signal error."""
        signals = [
            {"ticker": "AAPL", "confidence_score": 0.8, "signal_type": "buy"},
            {"ticker": "BAD", "confidence_score": "not_a_number", "signal_type": "buy"},
            {"ticker": "GOOG", "confidence_score": 0.6, "signal_type": "hold"},
        ]
        code = """
signal['confidence_score'] = float(signal['confidence_score']) + 0.1
result = signal
"""
        results, trace = apply_lambda_to_signals(signals, code)

        assert len(results) == 3
        assert len(trace.errors) == 1
        assert trace.errors[0]["ticker"] == "BAD"

    def test_preserves_ticker(self):
        """apply_lambda_to_signals preserves original ticker."""
        signals = [{"ticker": "AAPL", "confidence_score": 0.8, "signal_type": "buy"}]
        code = """
signal['ticker'] = 'HACKED'  # Try to change ticker
result = signal
"""
        results, trace = apply_lambda_to_signals(signals, code)

        # Ticker should be preserved as AAPL
        assert results[0]["ticker"] == "AAPL"


# =============================================================================
# Security Regression Tests
# =============================================================================

class TestSecurityRegressions:
    """Regression tests for previously discovered security issues."""

    @pytest.fixture
    def sandbox(self):
        return SignalLambdaSandbox()

    def test_cannot_access_os_via_builtins_bypass(self, sandbox):
        """Cannot access os module via __builtins__ bypass attempts."""
        # Various escape attempts that have been seen in the wild
        dangerous_codes = [
            "signal.__class__.__bases__[0].__subclasses__()",
            "().__class__.__bases__[0].__subclasses__()",
            "''.__class__.__mro__[1].__subclasses__()",
        ]
        for code in dangerous_codes:
            with pytest.raises(LambdaValidationError):
                sandbox.validate_code(code)

    def test_cannot_use_globals_lookup(self, sandbox):
        """Cannot use globals() to escape sandbox."""
        with pytest.raises(LambdaValidationError, match="Forbidden function"):
            sandbox.validate_code("globals()")

    def test_cannot_use_locals_lookup(self, sandbox):
        """Cannot use locals() to escape sandbox."""
        with pytest.raises(LambdaValidationError, match="Forbidden function"):
            sandbox.validate_code("locals()")

    def test_cannot_use_vars_lookup(self, sandbox):
        """Cannot use vars() to escape sandbox."""
        with pytest.raises(LambdaValidationError, match="Forbidden function"):
            sandbox.validate_code("vars()")

    def test_cannot_construct_type(self, sandbox):
        """Cannot use type() to construct new types."""
        with pytest.raises(LambdaValidationError, match="Forbidden function"):
            sandbox.validate_code("type('X', (), {})")

    def test_cannot_access_function_code(self, sandbox):
        """Cannot access __code__ attribute of functions."""
        with pytest.raises(LambdaValidationError, match="Forbidden.*__code__"):
            sandbox.validate_code("(lambda: None).__code__")
