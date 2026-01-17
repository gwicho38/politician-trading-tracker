"""
Sandboxed execution engine for user lambdas.

Provides a safe execution environment for user-defined signal transformers
using RestrictedPython for code validation and execution sandboxing.
"""

import ast
import copy
import logging
import math
import threading
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ExecutionTrace:
    """Captures execution details for observability."""
    console_output: List[str] = field(default_factory=list)
    execution_time_ms: float = 0
    signals_processed: int = 0
    signals_modified: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    sample_transformations: List[Dict[str, Any]] = field(default_factory=list)


class CapturedPrint:
    """Captures print() output for observability."""

    def __init__(self, max_lines: int = 100, max_chars_per_line: int = 500):
        self.output: List[str] = []
        self.max_lines = max_lines
        self.max_chars_per_line = max_chars_per_line

    def __call__(self, *args, **kwargs):
        """Callable that captures print output."""
        if len(self.output) >= self.max_lines:
            return  # Silently drop after limit

        # Convert args to string like print() does
        sep = kwargs.get('sep', ' ')
        end = kwargs.get('end', '\n')
        line = sep.join(str(arg) for arg in args)

        # Truncate long lines
        if len(line) > self.max_chars_per_line:
            line = line[:self.max_chars_per_line] + '...[truncated]'

        # Handle newlines in end
        if end and end != '\n':
            line += end.rstrip('\n')

        self.output.append(line)

    def get_output(self) -> List[str]:
        return self.output.copy()


class LambdaValidationError(Exception):
    """Raised when lambda code fails validation."""
    pass


class LambdaExecutionError(Exception):
    """Raised when lambda execution fails."""
    pass


class SignalLambdaSandbox:
    """Safe execution environment for user-defined signal transformers."""

    TIMEOUT_SECONDS = 5

    # Whitelist of safe builtins
    SAFE_BUILTINS = {
        'len': len,
        'abs': abs,
        'min': min,
        'max': max,
        'round': round,
        'str': str,
        'int': int,
        'float': float,
        'bool': bool,
        'list': list,
        'dict': dict,
        'tuple': tuple,
        'range': range,
        'sum': sum,
        'any': any,
        'all': all,
        'True': True,
        'False': False,
        'None': None,
        'pow': pow,
        'sorted': sorted,
        'enumerate': enumerate,
        'zip': zip,
        'map': map,
        'filter': filter,
    }

    # Dangerous AST node types to reject
    FORBIDDEN_NODES = {
        ast.Import,
        ast.ImportFrom,
        ast.Global,
        ast.Nonlocal,
        ast.AsyncFunctionDef,
        ast.AsyncFor,
        ast.AsyncWith,
        ast.Await,
        ast.Yield,
        ast.YieldFrom,
    }

    # Forbidden function calls
    FORBIDDEN_CALLS = {
        'eval',
        'exec',
        'compile',
        'open',
        '__import__',
        'globals',
        'locals',
        'vars',
        'dir',
        'getattr',
        'setattr',
        'delattr',
        'hasattr',
        'input',
        'breakpoint',
        'exit',
        'quit',
        'help',
        'license',
        'copyright',
        'credits',
        'memoryview',
        'bytearray',
        'bytes',
        'classmethod',
        'staticmethod',
        'property',
        'super',
        'type',
        'object',
        '__build_class__',
    }

    # Forbidden attribute access patterns
    FORBIDDEN_ATTRIBUTES = {
        '__class__',
        '__bases__',
        '__subclasses__',
        '__mro__',
        '__code__',
        '__globals__',
        '__builtins__',
        '__import__',
        '__dict__',
        '__module__',
        '__name__',
        '__qualname__',
        '__self__',
        '__func__',
        '__closure__',
        '__annotations__',
        '__kwdefaults__',
        '__defaults__',
        '__wrapped__',
        '__call__',
        '__delattr__',
        '__setattr__',
        '__getattribute__',
        '__reduce__',
        '__reduce_ex__',
        '__getstate__',
        '__setstate__',
        'func_code',
        'func_globals',
    }

    def validate_code(self, code: str) -> None:
        """Validate code structure before compilation."""
        if not code or not code.strip():
            raise LambdaValidationError("Empty code provided")

        # Limit code size
        if len(code) > 10000:
            raise LambdaValidationError("Code exceeds maximum size of 10000 characters")

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise LambdaValidationError(f"Syntax error: {e}")

        for node in ast.walk(tree):
            # Check for forbidden node types
            if type(node) in self.FORBIDDEN_NODES:
                raise LambdaValidationError(
                    f"Forbidden operation: {type(node).__name__}"
                )

            # Check for forbidden function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in self.FORBIDDEN_CALLS:
                        raise LambdaValidationError(
                            f"Forbidden function: {node.func.id}"
                        )

            # Check for forbidden attribute access
            if isinstance(node, ast.Attribute):
                if node.attr in self.FORBIDDEN_ATTRIBUTES:
                    raise LambdaValidationError(
                        f"Forbidden attribute access: {node.attr}"
                    )
                # Block double underscore attributes in general
                if node.attr.startswith('__') and node.attr.endswith('__'):
                    raise LambdaValidationError(
                        f"Forbidden dunder access: {node.attr}"
                    )

            # Check for string formatting that could be exploited
            if isinstance(node, ast.JoinedStr):
                # f-strings can access attributes, which we allow but monitor
                pass

    def compile_lambda(self, code: str) -> Any:
        """Compile code with validation."""
        self.validate_code(code)

        try:
            # Try to import RestrictedPython for additional safety
            from RestrictedPython import compile_restricted
            from RestrictedPython.Eval import default_guarded_getitem
            from RestrictedPython.Guards import (
                guarded_iter_unpack_sequence,
                safer_getattr,
            )

            result = compile_restricted(
                code,
                filename='<user_lambda>',
                mode='exec'
            )

            if result.errors:
                raise LambdaValidationError(
                    f"Compilation errors: {'; '.join(result.errors)}"
                )

            return {
                'code': result.code,
                'use_restricted': True,
                'guards': {
                    '_getattr_': safer_getattr,
                    '_getitem_': default_guarded_getitem,
                    '_iter_unpack_sequence_': guarded_iter_unpack_sequence,
                }
            }

        except ImportError:
            logger.warning("RestrictedPython not available, using basic validation only")
            # Fall back to basic compilation with our own validation
            compiled = compile(code, '<user_lambda>', 'exec')
            return {
                'code': compiled,
                'use_restricted': False,
                'guards': {}
            }

    def _create_safe_math_module(self) -> Dict[str, Any]:
        """Create a safe subset of the math module."""
        return {
            'pi': math.pi,
            'e': math.e,
            'sqrt': math.sqrt,
            'log': math.log,
            'log10': math.log10,
            'log2': math.log2,
            'exp': math.exp,
            'pow': math.pow,
            'floor': math.floor,
            'ceil': math.ceil,
            'trunc': math.trunc,
            'fabs': math.fabs,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'asin': math.asin,
            'acos': math.acos,
            'atan': math.atan,
            'atan2': math.atan2,
            'degrees': math.degrees,
            'radians': math.radians,
            'isnan': math.isnan,
            'isinf': math.isinf,
            'isfinite': math.isfinite,
        }

    def execute(
        self,
        compiled_data: Dict[str, Any],
        signal: Dict[str, Any],
        captured_print: Optional[CapturedPrint] = None,
    ) -> Dict[str, Any]:
        """Execute compiled lambda on a signal dictionary."""
        compiled_code = compiled_data['code']
        guards = compiled_data.get('guards', {})

        # Create a deep copy of the signal to prevent modifications to original
        signal_copy = copy.deepcopy(signal)

        # Create captured print if not provided
        if captured_print is None:
            captured_print = CapturedPrint()

        # Create restricted globals with print capture
        builtins_with_print = {
            **self.SAFE_BUILTINS,
            'print': captured_print,  # Capture print output
        }

        restricted_globals = {
            '__builtins__': builtins_with_print,
            'math': self._create_safe_math_module(),
            'Decimal': Decimal,
            **guards,  # Add RestrictedPython guards if available
        }

        # Create locals with signal
        restricted_locals = {
            'signal': signal_copy,
            'result': None,
        }

        # Execute with timeout using threading
        execution_error = [None]
        execution_result = [None]

        def execute_code():
            try:
                exec(compiled_code, restricted_globals, restricted_locals)
                # Get result - either explicit 'result' or modified 'signal'
                execution_result[0] = restricted_locals.get('result') or restricted_locals.get('signal')
            except Exception as e:
                execution_error[0] = e

        thread = threading.Thread(target=execute_code)
        thread.daemon = True
        thread.start()
        thread.join(timeout=self.TIMEOUT_SECONDS)

        if thread.is_alive():
            # Thread is still running - timeout occurred
            raise LambdaExecutionError("Lambda execution timed out")

        if execution_error[0]:
            raise LambdaExecutionError(f"Execution error: {execution_error[0]}")

        result = execution_result[0]

        # Validate result is a dict (signal-like object)
        if not isinstance(result, dict):
            raise LambdaExecutionError(
                f"Lambda must return a dict (signal), got {type(result).__name__}"
            )

        # Validate critical fields are present
        if 'ticker' not in result:
            raise LambdaExecutionError("Result missing required 'ticker' field")

        return result


def _signal_was_modified(original: Dict[str, Any], modified: Dict[str, Any]) -> bool:
    """Check if a signal was modified by comparing key fields."""
    fields_to_check = ['confidence_score', 'signal_type', 'signal_strength']
    for field in fields_to_check:
        if original.get(field) != modified.get(field):
            return True
    return False


def apply_lambda_to_signals(
    signals: List[Dict[str, Any]],
    lambda_code: str,
    collect_trace: bool = True,
) -> tuple[List[Dict[str, Any]], ExecutionTrace]:
    """
    Apply a user lambda to a list of signals.

    Args:
        signals: List of signal dictionaries
        lambda_code: User-provided Python code
        collect_trace: Whether to collect execution trace for observability

    Returns:
        Tuple of (transformed signals list, execution trace)
    """
    sandbox = SignalLambdaSandbox()
    trace = ExecutionTrace()
    start_time = time.time()

    # Shared print capture across all signals
    captured_print = CapturedPrint()

    try:
        compiled = sandbox.compile_lambda(lambda_code)
    except LambdaValidationError as e:
        logger.warning(f"Lambda validation failed: {e}")
        raise

    results = []
    modified_count = 0
    max_sample_transformations = 3  # Show up to 3 examples

    for i, signal in enumerate(signals):
        try:
            modified = sandbox.execute(compiled, signal, captured_print)
            # Preserve original ticker even if lambda tries to change it
            modified['ticker'] = signal.get('ticker', modified.get('ticker'))
            results.append(modified)

            # Track if signal was modified
            was_modified = _signal_was_modified(signal, modified)
            if was_modified:
                modified_count += 1

                # Collect sample transformations for observability
                if collect_trace and len(trace.sample_transformations) < max_sample_transformations:
                    trace.sample_transformations.append({
                        'ticker': signal.get('ticker'),
                        'before': {
                            'signal_type': signal.get('signal_type'),
                            'confidence_score': signal.get('confidence_score'),
                            'signal_strength': signal.get('signal_strength'),
                        },
                        'after': {
                            'signal_type': modified.get('signal_type'),
                            'confidence_score': modified.get('confidence_score'),
                            'signal_strength': modified.get('signal_strength'),
                        },
                    })

        except LambdaExecutionError as e:
            logger.warning(f"Lambda execution failed for signal {i} ({signal.get('ticker')}): {e}")
            trace.errors.append({'index': i, 'ticker': signal.get('ticker'), 'error': str(e)})
            results.append(signal)  # Keep original on error

    # Finalize trace
    trace.execution_time_ms = (time.time() - start_time) * 1000
    trace.signals_processed = len(signals)
    trace.signals_modified = modified_count
    trace.console_output = captured_print.get_output()

    if trace.errors:
        logger.info(f"Lambda applied with {len(trace.errors)} errors out of {len(signals)} signals")

    return results, trace
