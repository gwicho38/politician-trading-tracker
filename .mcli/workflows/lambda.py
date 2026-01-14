"""Lambda sandbox testing and validation commands."""

import os
import json
import time
from typing import Optional

import click
import httpx

# Configuration
ETL_SERVICE_URL = os.environ.get(
    "ETL_SERVICE_URL",
    "https://politician-trading-etl.fly.dev"
)


@click.group(name="lambda")
def lambda_cmd():
    """Test and validate user lambda functions for signal transformation."""
    pass


# =============================================================================
# Validation Commands
# =============================================================================

@lambda_cmd.command(name="validate")
@click.argument("code", required=False)
@click.option("--file", "-f", type=click.Path(exists=True), help="Read code from file")
def validate(code: Optional[str], file: Optional[str]):
    """
    Validate lambda code without executing it.

    Examples:
        mcli run lambda validate 'result = signal'
        mcli run lambda validate -f my_lambda.py
    """
    if file:
        with open(file, 'r') as f:
            code = f.read()

    if not code:
        click.echo("Error: Provide code as argument or use --file", err=True)
        raise SystemExit(1)

    click.echo("🔍 Validating lambda code...\n")
    click.echo(f"Code:\n{'-'*40}")
    for line in code.split('\n')[:10]:
        click.echo(f"  {line}")
    if code.count('\n') > 10:
        click.echo(f"  ... ({code.count(chr(10)) - 10} more lines)")
    click.echo(f"{'-'*40}\n")

    try:
        response = httpx.post(
            f"{ETL_SERVICE_URL}/signals/validate-lambda",
            json={"lambdaCode": code},
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()

        if data.get("valid"):
            click.echo("✅ Lambda code is valid")
        else:
            click.echo(f"❌ Invalid: {data.get('error', 'Unknown error')}")
            raise SystemExit(1)

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@lambda_cmd.command(name="test-security")
def test_security():
    """
    Test that dangerous operations are properly blocked.

    Runs a suite of security tests against the sandbox.
    """
    click.echo("🔒 Security Test Suite\n")

    test_cases = [
        ("Import blocking", "import os\nresult = signal", False),
        ("Import from blocking", "from os import path\nresult = signal", False),
        ("Eval blocking", "eval('1+1')\nresult = signal", False),
        ("Exec blocking", "exec('x=1')\nresult = signal", False),
        ("Open blocking", "open('/etc/passwd')\nresult = signal", False),
        ("__import__ blocking", "__import__('os')\nresult = signal", False),
        ("Dunder class access", "signal.__class__.__bases__\nresult = signal", False),
        ("Dunder globals access", "().__class__.__globals__\nresult = signal", False),
        ("Getattr blocking", "getattr(signal, 'ticker')\nresult = signal", False),
        ("Valid simple lambda", "result = signal", True),
        ("Valid math operations", "signal['confidence_score'] = min(0.99, signal['confidence_score'] + 0.1)\nresult = signal", True),
        ("Valid conditional", "if signal.get('buy_sell_ratio', 0) > 2:\n    signal['confidence_score'] = 0.9\nresult = signal", True),
    ]

    passed = 0
    failed = 0

    for name, code, should_pass in test_cases:
        try:
            response = httpx.post(
                f"{ETL_SERVICE_URL}/signals/validate-lambda",
                json={"lambdaCode": code},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()

            is_valid = data.get("valid", False)

            if is_valid == should_pass:
                status = "✅ PASS"
                passed += 1
            else:
                status = "❌ FAIL"
                failed += 1
                if should_pass:
                    status += f" (expected valid, got: {data.get('error', 'invalid')})"
                else:
                    status += " (expected blocked, but passed)"

            click.echo(f"  {status}: {name}")

        except httpx.HTTPError as e:
            click.echo(f"  ❌ ERROR: {name} - {e}")
            failed += 1

    click.echo(f"\n{'='*40}")
    click.echo(f"Results: {passed} passed, {failed} failed")

    if failed > 0:
        raise SystemExit(1)


# =============================================================================
# Execution Commands
# =============================================================================

@lambda_cmd.command(name="apply")
@click.option("--code", "-c", required=True, help="Lambda code to apply")
@click.option("--ticker", "-t", default="AAPL", help="Ticker symbol")
@click.option("--confidence", default=0.7, help="Initial confidence score")
@click.option("--signal-type", default="buy", help="Signal type")
@click.option("--buy-sell-ratio", "-r", default=2.0, help="Buy/sell ratio")
@click.option("--politician-count", "-p", default=3, help="Politician activity count")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def apply(code: str, ticker: str, confidence: float, signal_type: str,
          buy_sell_ratio: float, politician_count: int, as_json: bool):
    """
    Apply lambda code to a test signal.

    Examples:
        mcli run lambda apply -c 'signal["confidence_score"] = 0.99; result = signal'
        mcli run lambda apply -c 'result = signal' -t NVDA --confidence 0.8
        mcli run lambda apply -c 'if signal["buy_sell_ratio"] > 2: signal["confidence_score"] += 0.1; result = signal' -r 3.0
    """
    signal = {
        "ticker": ticker.upper(),
        "signal_type": signal_type,
        "confidence_score": confidence,
        "buy_sell_ratio": buy_sell_ratio,
        "politician_activity_count": politician_count,
        "total_transaction_volume": 100000,
        "ml_enhanced": False,
    }

    click.echo("🧪 Applying lambda to test signal\n")

    if not as_json:
        click.echo(f"Input signal:")
        click.echo(f"  Ticker: {signal['ticker']}")
        click.echo(f"  Type: {signal['signal_type']}")
        click.echo(f"  Confidence: {signal['confidence_score']:.2f}")
        click.echo(f"  Buy/Sell Ratio: {signal['buy_sell_ratio']:.1f}")
        click.echo(f"  Politicians: {signal['politician_activity_count']}")
        click.echo()

    try:
        response = httpx.post(
            f"{ETL_SERVICE_URL}/signals/apply-lambda",
            json={
                "signals": [signal],
                "lambdaCode": code
            },
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()

        if as_json:
            click.echo(json.dumps(data, indent=2))
            return

        if data.get("success") and data.get("signals"):
            result = data["signals"][0]
            click.echo("Output signal:")
            click.echo(f"  Ticker: {result.get('ticker')}")
            click.echo(f"  Type: {result.get('signal_type')}")
            click.echo(f"  Confidence: {result.get('confidence_score', 0):.2f}")

            # Show what changed
            changes = []
            if result.get('confidence_score') != signal['confidence_score']:
                diff = result.get('confidence_score', 0) - signal['confidence_score']
                changes.append(f"confidence {'+' if diff > 0 else ''}{diff:.2f}")
            if result.get('signal_type') != signal['signal_type']:
                changes.append(f"type: {signal['signal_type']} → {result.get('signal_type')}")

            if changes:
                click.echo(f"\n✓ Changes: {', '.join(changes)}")
            else:
                click.echo("\n○ No changes")
        else:
            click.echo(f"❌ Lambda failed: {data}")
            raise SystemExit(1)

    except httpx.HTTPStatusError as e:
        error_detail = e.response.json() if e.response.headers.get('content-type', '').startswith('application/json') else e.response.text
        click.echo(f"❌ Error: {error_detail}", err=True)
        raise SystemExit(1)
    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@lambda_cmd.command(name="batch")
@click.option("--code", "-c", required=True, help="Lambda code to apply")
@click.option("--count", "-n", default=10, help="Number of test signals")
def batch(code: str, count: int):
    """
    Test lambda on multiple signals.

    Examples:
        mcli run lambda batch -c 'signal["confidence_score"] *= 1.1; result = signal' -n 20
    """
    # Generate test signals
    signals = [
        {
            "ticker": f"TEST{i}",
            "signal_type": ["strong_buy", "buy", "hold", "sell", "strong_sell"][i % 5],
            "confidence_score": 0.5 + (i % 5) * 0.1,
            "buy_sell_ratio": 0.5 + i * 0.3,
            "politician_activity_count": i % 8,
            "total_transaction_volume": 10000 * (i + 1),
            "ml_enhanced": i % 2 == 0,
        }
        for i in range(count)
    ]

    click.echo(f"🧪 Batch Lambda Test\n")
    click.echo(f"  Signals: {count}")
    click.echo(f"  Code: {code[:50]}{'...' if len(code) > 50 else ''}")
    click.echo()

    try:
        start = time.time()
        response = httpx.post(
            f"{ETL_SERVICE_URL}/signals/apply-lambda",
            json={
                "signals": signals,
                "lambdaCode": code
            },
            timeout=60.0
        )
        elapsed = time.time() - start

        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            results = data.get("signals", [])
            click.echo(f"✓ Processed {len(results)} signals in {elapsed:.2f}s")
            click.echo(f"  Per signal: {elapsed * 1000 / count:.1f}ms")

            # Show sample of changes
            changes = 0
            for orig, result in zip(signals, results):
                if orig["confidence_score"] != result.get("confidence_score"):
                    changes += 1

            click.echo(f"  Signals modified: {changes}/{count}")
        else:
            click.echo(f"❌ Batch failed: {data}")

    except httpx.HTTPError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# =============================================================================
# Help & Examples
# =============================================================================

@lambda_cmd.command(name="help")
def show_help():
    """
    Show lambda help documentation and examples.
    """
    try:
        response = httpx.get(
            f"{ETL_SERVICE_URL}/signals/lambda-help",
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()

        click.echo("📚 Lambda Help\n")
        click.echo(f"{data.get('description', '')}\n")

        click.echo("Signal Fields:")
        for field, desc in data.get("signal_fields", {}).items():
            click.echo(f"  {field}: {desc}")

        click.echo("\nAvailable Builtins:")
        builtins = data.get("available_builtins", [])
        click.echo(f"  {', '.join(builtins)}")

        click.echo("\nForbidden Operations:")
        for op in data.get("forbidden_operations", []):
            click.echo(f"  ❌ {op}")

        click.echo("\nExamples:")
        for example in data.get("examples", [])[:3]:
            click.echo(f"\n  {example.get('name')}:")
            for line in example.get("code", "").split('\n'):
                click.echo(f"    {line}")

        click.echo("\nTips:")
        for tip in data.get("tips", []):
            click.echo(f"  • {tip}")

    except httpx.HTTPError as e:
        click.echo(f"Error fetching help: {e}", err=True)

        # Show local fallback help
        click.echo("\n📚 Lambda Quick Reference\n")
        click.echo("Available in lambda:")
        click.echo("  - signal: dict with ticker, confidence_score, signal_type, etc.")
        click.echo("  - math: sqrt, log, sin, cos, floor, ceil, etc.")
        click.echo("  - Decimal: for precise arithmetic")
        click.echo("  - Builtins: len, abs, min, max, round, str, int, float")
        click.echo("\nExample:")
        click.echo('  if signal.get("buy_sell_ratio", 0) > 2:')
        click.echo('      signal["confidence_score"] = min(signal["confidence_score"] + 0.1, 0.99)')
        click.echo('  result = signal')


@lambda_cmd.command(name="examples")
def show_examples():
    """
    Show example lambda functions.
    """
    examples = [
        {
            "name": "Boost high buy/sell ratio",
            "description": "Increase confidence when buy/sell ratio is favorable",
            "code": '''if signal.get("buy_sell_ratio", 0) > 3.0:
    signal["confidence_score"] = min(signal["confidence_score"] + 0.1, 0.99)
result = signal'''
        },
        {
            "name": "Penalize low politician count",
            "description": "Reduce confidence for signals with few politicians",
            "code": '''if signal.get("politician_activity_count", 0) < 3:
    signal["confidence_score"] = signal["confidence_score"] * 0.85
result = signal'''
        },
        {
            "name": "Convert weak sells to holds",
            "description": "Change low-confidence sell signals to hold",
            "code": '''if signal["signal_type"] == "sell" and signal["confidence_score"] < 0.65:
    signal["signal_type"] = "hold"
result = signal'''
        },
        {
            "name": "Volume-based boost",
            "description": "Boost confidence for high-volume signals",
            "code": '''volume = signal.get("total_transaction_volume", 0)
if volume > 500000:
    signal["confidence_score"] = min(signal["confidence_score"] + 0.15, 0.99)
elif volume > 100000:
    signal["confidence_score"] = min(signal["confidence_score"] + 0.05, 0.99)
result = signal'''
        },
        {
            "name": "Logarithmic scaling",
            "description": "Apply log scaling to confidence scores",
            "code": '''score = signal["confidence_score"]
signal["confidence_score"] = min(0.5 + math.log(1 + score) / 2, 0.99)
result = signal'''
        },
    ]

    click.echo("📝 Lambda Examples\n")

    for i, ex in enumerate(examples, 1):
        click.echo(f"{i}. {ex['name']}")
        click.echo(f"   {ex['description']}\n")
        click.echo("   Code:")
        for line in ex["code"].split('\n'):
            click.echo(f"     {line}")
        click.echo()


@lambda_cmd.command(name="test-all")
def test_all():
    """
    Run comprehensive lambda tests (security + functionality).
    """
    click.echo("🧪 Comprehensive Lambda Test Suite\n")
    click.echo("="*50)

    # Security tests
    click.echo("\n1️⃣ Security Tests\n")

    security_tests = [
        ("import os", False, "Import blocking"),
        ("eval('1')", False, "Eval blocking"),
        ("open('/tmp/x')", False, "File I/O blocking"),
        ("signal.__class__", False, "Dunder blocking"),
        ("result = signal", True, "Basic passthrough"),
    ]

    security_passed = 0
    for code, should_pass, name in security_tests:
        try:
            response = httpx.post(
                f"{ETL_SERVICE_URL}/signals/validate-lambda",
                json={"lambdaCode": code},
                timeout=10.0
            )
            data = response.json()
            is_valid = data.get("valid", False)

            if is_valid == should_pass:
                click.echo(f"  ✅ {name}")
                security_passed += 1
            else:
                click.echo(f"  ❌ {name}")
        except Exception as e:
            click.echo(f"  ❌ {name}: {e}")

    click.echo(f"\n  Security: {security_passed}/{len(security_tests)} passed")

    # Functionality tests
    click.echo("\n2️⃣ Functionality Tests\n")

    func_tests = [
        (
            "Confidence increase",
            'signal["confidence_score"] = 0.99; result = signal',
            {"ticker": "TEST", "confidence_score": 0.5},
            lambda r: r.get("confidence_score") == 0.99
        ),
        (
            "Conditional logic",
            'if signal.get("buy_sell_ratio", 0) > 2: signal["confidence_score"] = 0.9\nresult = signal',
            {"ticker": "TEST", "confidence_score": 0.5, "buy_sell_ratio": 3.0},
            lambda r: r.get("confidence_score") == 0.9
        ),
        (
            "Math operations",
            'signal["confidence_score"] = round(signal["confidence_score"] * 2, 2); result = signal',
            {"ticker": "TEST", "confidence_score": 0.4},
            lambda r: r.get("confidence_score") == 0.8
        ),
        (
            "Signal type change",
            'signal["signal_type"] = "hold"; result = signal',
            {"ticker": "TEST", "confidence_score": 0.5, "signal_type": "buy"},
            lambda r: r.get("signal_type") == "hold"
        ),
    ]

    func_passed = 0
    for name, code, signal, check in func_tests:
        try:
            response = httpx.post(
                f"{ETL_SERVICE_URL}/signals/apply-lambda",
                json={"signals": [signal], "lambdaCode": code},
                timeout=10.0
            )
            data = response.json()

            if data.get("success") and data.get("signals"):
                result = data["signals"][0]
                if check(result):
                    click.echo(f"  ✅ {name}")
                    func_passed += 1
                else:
                    click.echo(f"  ❌ {name}: unexpected result {result}")
            else:
                click.echo(f"  ❌ {name}: {data}")
        except Exception as e:
            click.echo(f"  ❌ {name}: {e}")

    click.echo(f"\n  Functionality: {func_passed}/{len(func_tests)} passed")

    # Summary
    total = len(security_tests) + len(func_tests)
    passed = security_passed + func_passed

    click.echo("\n" + "="*50)
    click.echo(f"Total: {passed}/{total} tests passed")

    if passed < total:
        raise SystemExit(1)
