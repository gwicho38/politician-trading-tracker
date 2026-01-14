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
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


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
    ) -> Dict[str, Any]:
        """Execute compiled lambda on a signal dictionary."""
        compiled_code = compiled_data['code']
        guards = compiled_data.get('guards', {})

        # Create a deep copy of the signal to prevent modifications to original
        signal_copy = copy.deepcopy(signal)

        # Create restricted globals
        restricted_globals = {
            '__builtins__': self.SAFE_BUILTINS,
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


def apply_lambda_to_signals(
    signals: List[Dict[str, Any]],
    lambda_code: str,
) -> List[Dict[str, Any]]:
    """
    Apply a user lambda to a list of signals.

    Args:
        signals: List of signal dictionaries
        lambda_code: User-provided Python code

    Returns:
        List of transformed signals (or original on error)
    """
    sandbox = SignalLambdaSandbox()

    try:
        compiled = sandbox.compile_lambda(lambda_code)
    except LambdaValidationError as e:
        logger.warning(f"Lambda validation failed: {e}")
        raise

    results = []
    errors = []

    for i, signal in enumerate(signals):
        try:
            modified = sandbox.execute(compiled, signal)
            # Preserve original ticker even if lambda tries to change it
            modified['ticker'] = signal.get('ticker', modified.get('ticker'))
            results.append(modified)
        except LambdaExecutionError as e:
            logger.warning(f"Lambda execution failed for signal {i} ({signal.get('ticker')}): {e}")
            errors.append({'index': i, 'ticker': signal.get('ticker'), 'error': str(e)})
            results.append(signal)  # Keep original on error

    if errors:
        logger.info(f"Lambda applied with {len(errors)} errors out of {len(signals)} signals")

    return results
