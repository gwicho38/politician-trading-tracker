"""
Signal Lambda API Routes

Endpoints for applying user-defined lambdas to trading signals.
"""

import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.sandbox import (
    SignalLambdaSandbox,
    apply_lambda_to_signals,
    LambdaValidationError,
    LambdaExecutionError,
    ExecutionTrace,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class SignalDict(BaseModel):
    """Signal object as a dictionary."""
    ticker: str
    asset_name: Optional[str] = None
    signal_type: str
    signal_strength: Optional[str] = None
    confidence_score: float
    politician_activity_count: Optional[int] = None
    buy_sell_ratio: Optional[float] = None
    total_transaction_volume: Optional[float] = None
    ml_enhanced: Optional[bool] = None
    features: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"  # Allow additional fields


class ApplyLambdaRequest(BaseModel):
    """Request body for applying a lambda to signals."""
    signals: List[Dict[str, Any]] = Field(
        ...,
        description="List of signal dictionaries to transform"
    )
    lambdaCode: str = Field(
        ...,
        description="Python code to apply to each signal"
    )


class SampleTransformation(BaseModel):
    """Sample before/after transformation for observability."""
    ticker: str
    before: Dict[str, Any]
    after: Dict[str, Any]


class ExecutionTraceResponse(BaseModel):
    """Execution trace for observability."""
    console_output: List[str] = Field(default_factory=list)
    execution_time_ms: float = 0
    signals_processed: int = 0
    signals_modified: int = 0
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    sample_transformations: List[SampleTransformation] = Field(default_factory=list)


class ApplyLambdaResponse(BaseModel):
    """Response from lambda application."""
    success: bool
    signals: List[Dict[str, Any]]
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    message: Optional[str] = None
    trace: Optional[ExecutionTraceResponse] = None


class ValidateLambdaRequest(BaseModel):
    """Request body for validating lambda code."""
    lambdaCode: str


class ValidateLambdaResponse(BaseModel):
    """Response from lambda validation."""
    valid: bool
    error: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/apply-lambda", response_model=ApplyLambdaResponse)
async def apply_lambda(request: ApplyLambdaRequest):
    """
    Apply a user-defined lambda to a list of signals.

    The lambda code has access to a 'signal' dictionary and should
    assign the result to 'result' or modify 'signal' directly.

    Example lambda code:
    ```python
    # Boost confidence for high buy/sell ratio
    if signal.get('buy_sell_ratio', 0) > 3.0:
        signal['confidence_score'] = min(signal['confidence_score'] + 0.05, 0.99)

    result = signal
    ```

    Available in the lambda:
    - signal: The current signal dictionary
    - math: Safe math functions (sqrt, log, sin, cos, etc.)
    - Decimal: For precise decimal arithmetic
    - Basic builtins: len, abs, min, max, round, str, int, float, etc.

    Forbidden operations:
    - import statements
    - eval, exec, compile
    - File I/O (open, read, write)
    - Network access
    - Attribute access to dunder methods
    """
    if not request.signals:
        return ApplyLambdaResponse(
            success=True,
            signals=[],
            message="No signals provided",
            trace=ExecutionTraceResponse()
        )

    if not request.lambdaCode or not request.lambdaCode.strip():
        return ApplyLambdaResponse(
            success=True,
            signals=request.signals,
            message="Empty lambda code, returning original signals",
            trace=ExecutionTraceResponse(signals_processed=len(request.signals))
        )

    try:
        # Apply the lambda to all signals with trace collection
        transformed_signals, trace = apply_lambda_to_signals(
            request.signals,
            request.lambdaCode,
            collect_trace=True
        )

        # Convert trace to response format
        trace_response = ExecutionTraceResponse(
            console_output=trace.console_output,
            execution_time_ms=round(trace.execution_time_ms, 2),
            signals_processed=trace.signals_processed,
            signals_modified=trace.signals_modified,
            errors=trace.errors,
            sample_transformations=[
                SampleTransformation(**t) for t in trace.sample_transformations
            ]
        )

        return ApplyLambdaResponse(
            success=True,
            signals=transformed_signals,
            message=f"Lambda applied: {trace.signals_modified}/{trace.signals_processed} signals modified",
            trace=trace_response
        )

    except LambdaValidationError as e:
        logger.warning(f"Lambda validation failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid lambda code: {str(e)}"
        )

    except LambdaExecutionError as e:
        logger.warning(f"Lambda execution failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Lambda execution error: {str(e)}"
        )

    except Exception as e:
        logger.error(f"Unexpected error in apply_lambda: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )


@router.post("/validate-lambda", response_model=ValidateLambdaResponse)
async def validate_lambda(request: ValidateLambdaRequest):
    """
    Validate lambda code without executing it.

    Returns whether the code passes all validation checks.
    """
    if not request.lambdaCode or not request.lambdaCode.strip():
        return ValidateLambdaResponse(valid=False, error="Empty code provided")

    sandbox = SignalLambdaSandbox()

    try:
        sandbox.validate_code(request.lambdaCode)
        # Also try to compile it
        sandbox.compile_lambda(request.lambdaCode)
        return ValidateLambdaResponse(valid=True)

    except LambdaValidationError as e:
        return ValidateLambdaResponse(valid=False, error=str(e))

    except Exception as e:
        return ValidateLambdaResponse(valid=False, error=f"Validation error: {str(e)}")


@router.get("/lambda-help")
async def lambda_help():
    """
    Get help documentation for writing signal lambdas.
    """
    return {
        "description": "User lambdas allow you to transform trading signals with custom Python logic.",
        "signal_fields": {
            "ticker": "Stock ticker symbol (string)",
            "asset_name": "Full asset name (string)",
            "signal_type": "Signal type: 'strong_buy', 'buy', 'hold', 'sell', 'strong_sell'",
            "signal_strength": "Signal strength: 'very_strong', 'strong', 'moderate', 'weak'",
            "confidence_score": "Confidence score (float, 0.0-1.0)",
            "politician_activity_count": "Number of politicians trading this ticker",
            "buy_sell_ratio": "Ratio of buy to sell transactions",
            "total_transaction_volume": "Total transaction volume in dollars",
            "ml_enhanced": "Whether ML model was used (boolean)",
            "features": "Additional feature data (dict)",
        },
        "available_builtins": [
            "len", "abs", "min", "max", "round", "str", "int", "float",
            "bool", "list", "dict", "tuple", "range", "sum", "any", "all",
            "pow", "sorted", "enumerate", "zip", "map", "filter"
        ],
        "available_modules": {
            "math": ["sqrt", "log", "log10", "exp", "pow", "floor", "ceil", "sin", "cos", "tan", "pi", "e"],
            "Decimal": "For precise decimal arithmetic",
        },
        "forbidden_operations": [
            "import statements",
            "eval, exec, compile",
            "File I/O (open)",
            "Network access",
            "Dunder attribute access (__class__, __globals__, etc.)",
        ],
        "examples": [
            {
                "name": "Boost high buy/sell ratio",
                "code": """if signal.get('buy_sell_ratio', 0) > 3.0:
    signal['confidence_score'] = min(signal['confidence_score'] + 0.05, 0.99)
result = signal"""
            },
            {
                "name": "Penalize low politician count",
                "code": """if signal.get('politician_activity_count', 0) < 3:
    signal['confidence_score'] = signal['confidence_score'] * 0.9
result = signal"""
            },
            {
                "name": "Convert weak sells to holds",
                "code": """if signal['signal_type'] == 'sell' and signal['confidence_score'] < 0.7:
    signal['signal_type'] = 'hold'
    signal['signal_strength'] = 'weak'
result = signal"""
            },
            {
                "name": "Apply logarithmic confidence scaling",
                "code": """import_error = False  # imports are forbidden
score = signal['confidence_score']
# Use math.log for logarithmic scaling
scaled = 0.5 + (math.log(1 + score) / math.log(2)) * 0.5
signal['confidence_score'] = min(scaled, 0.99)
result = signal"""
            },
        ],
        "tips": [
            "Always assign your final signal to 'result' or modify 'signal' directly",
            "Use .get() for optional fields to avoid KeyError",
            "Confidence scores should stay between 0 and 1",
            "The lambda runs with a 5-second timeout per signal",
            "Keep logic simple - complex lambdas may timeout",
        ],
    }
