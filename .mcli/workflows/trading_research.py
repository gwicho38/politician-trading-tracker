#!/usr/bin/env python3
# @description: Autonomous trading parameter research loop (autoresearch-style)
# @version: 1.0.0
# @group: research

"""
Autoresearch-style parameter optimization for the trading system.

Maps autoresearch concepts to the trading domain:

  autoresearch          →  trading_research
  ─────────────────────────────────────────────
  train.py              →  trading_params.py
  prepare.py            →  backtest_parameters.py (fixed)
  val_bpb               →  profit_factor
  5-min GPU budget      →  backtest on closed positions
  program.md            →  research_program.md
  results.tsv           →  research_results.tsv
  autonomous loop       →  mcli run trading research

Usage:
    mcli run trading research run              # 10 iterations, optimize profit_factor
    mcli run trading research run -n 25        # 25 iterations
    mcli run trading research run --baseline-only  # just print baseline metrics
    mcli run trading research status           # show results history
    mcli run trading research params           # show current trading_params.py
"""

import os
import re
import csv
import signal
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

import logging

import anthropic
import click

# ──────────────────────────────────────────────────────────────────
# Graceful stop: pressing 'q' + Enter OR Ctrl+C both trigger clean exit
# ──────────────────────────────────────────────────────────────────
_stop_requested = threading.Event()

# Suggestions extracted from the most recent backtest run (populated as a side-effect of
# _run_backtest so callers don't need to change their signature).
_last_backtest_suggestions: list[str] = []

# Keywords that flag a suggestion as requiring a CODE change (not just parameter tuning).
_CODE_SUGGESTION_KEYWORDS = [
    "ml pre-filter",
    "improve signal quality",
    "pre-filter gate",
    "ml confidence filter",
    "retrain",
    "feature",
]


def _start_quit_listener() -> None:
    """Background thread: set _stop_requested when user types 'q' + Enter."""
    def _listen():
        try:
            for line in sys.stdin:
                if line.strip().lower() == "q":
                    _stop_requested.set()
                    break
        except Exception:
            pass
    t = threading.Thread(target=_listen, daemon=True)
    t.start()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ──────────────────────────────────────────────────────────────────
# Paths (resolved relative to this workflow file)
# ──────────────────────────────────────────────────────────────────
_WORKFLOWS_DIR = Path(__file__).parent
_REPO_ROOT = _WORKFLOWS_DIR.parent.parent  # politician-trading-tracker/
_SCRIPTS_DIR = _REPO_ROOT / "python-etl-service" / "scripts"
_PARAMS_FILE = _SCRIPTS_DIR / "trading_params.py"
_BACKTEST_SCRIPT = _SCRIPTS_DIR / "backtest_parameters.py"
_PROGRAM_FILE = _SCRIPTS_DIR / "research_program.md"
_RESULTS_FILE = _SCRIPTS_DIR / "research_results.tsv"
_ETL_ROOT = _REPO_ROOT / "python-etl-service"

RESULTS_HEADER = ["timestamp", "iteration", "profit_factor", "ev_per_trade", "win_rate", "n", "status", "description"]


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def _log(msg: str) -> None:
    """Timestamped print that flushes immediately."""
    ts = datetime.utcnow().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _extract_code_suggestions(output: str) -> list[str]:
    """Parse 'Recommended actions' block from backtest output.

    Returns only suggestions that require CODE changes (not parameter tuning),
    identified by _CODE_SUGGESTION_KEYWORDS.
    """
    suggestions: list[str] = []
    in_block = False
    for line in output.splitlines():
        clean = line.strip().lstrip("│").strip().lstrip("-").strip()
        if "Recommended actions:" in clean:
            in_block = True
            continue
        if in_block:
            if not clean or clean.startswith("=") or clean.startswith("─"):
                break
            if any(kw in clean.lower() for kw in _CODE_SUGGESTION_KEYWORDS):
                suggestions.append(clean)
    return suggestions


def _spawn_implementation_agent(
    suggestions: list[str],
    provider: str = "claude-cli",
    ollama_model: str = "mistral:instruct",
) -> bool:
    """Spawn a coding agent to implement code-level improvements suggested by the backtest.

    Provider selection:
      claude-cli  →  `claude -p <prompt>`          (Claude Code)
      ollama      →  `opencode run -m ollama/<model> <prompt>`
      anthropic   →  `claude -p <prompt>`           (falls back to Claude Code)

    The agent reads the codebase, implements the highest-impact suggestion,
    runs tests, commits, and pushes. Returns True if it exited cleanly.
    """
    if not suggestions:
        return True

    suggestion_text = "\n".join(f"  - {s}" for s in suggestions)
    prompt = f"""You are improving a live trading system. The backtest loop has stalled on
parameter tuning and the backtest itself is recommending code-level changes:

{suggestion_text}

Working directory: {_REPO_ROOT}

Key files:
  python-etl-service/app/services/ml_signal_model.py      — ML model
  python-etl-service/app/services/feature_pipeline.py     — feature engineering
  python-etl-service/scripts/backtest_parameters.py       — backtest harness
  supabase/functions/trading-signals/index.ts             — signal generation + pre-filter gate
  supabase/functions/reference-portfolio/index.ts         — position management

Context on the ML confidence miscalibration (CRITICAL):
  - [0.70, 0.75) band: 14% win rate  ← best
  - [0.75, 0.80) band: 12% win rate
  - [0.80, 1.00] band:  5% win rate  ← worst (paradoxically high confidence = bad)
  - Current MIN_SIGNAL_CONFIDENCE = 0.70 already gates entry
  - A pre-filter that EXCLUDES the [0.80+] band may improve outcomes

Task: implement the single highest-impact code change from the list above.
Prefer changes to the backtest and signal generation pipeline over UI changes.

Steps:
1. Read the relevant files
2. Implement the change (with tests if the test file exists nearby)
3. Run: cd python-etl-service && uv run pytest -x -q 2>&1 | tail -20
4. Commit: git add -A && git commit -m "feat: <one-line description of change>"
5. Push: git push

Implement ONE change. Do not over-engineer or add unrelated improvements."""

    _log("=" * 55)
    _log("SPAWNING IMPLEMENTATION AGENT")
    _log(f"Provider : {provider}" + (f" ({ollama_model})" if provider == "ollama" else ""))
    _log(f"Suggestions: {suggestions}")
    _log("Agent will implement, test, commit, and push.")
    _log("=" * 55)

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)

    if provider == "ollama":
        cmd = ["opencode", "run", "-m", f"ollama/{ollama_model}", prompt]
    else:
        # claude-cli or anthropic both use `claude -p`
        cmd = ["claude", "-p", prompt]

    try:
        result = subprocess.run(
            cmd,
            cwd=str(_REPO_ROOT),
            text=True,
            timeout=600,  # 10 minutes
            env=env,
        )
        if result.returncode == 0:
            _log("AGENT COMPLETE ✓")
            return True
        else:
            _log(f"[warn] Agent exited with code {result.returncode}")
            return False
    except subprocess.TimeoutExpired:
        _log("[warn] Implementation agent timed out after 10m")
        return False
    except FileNotFoundError as exc:
        cli = "opencode" if provider == "ollama" else "claude"
        _log(f"[warn] `{cli}` not found — skipping code agent ({exc})")
        return False
    except Exception as exc:
        _log(f"[warn] Implementation agent failed: {exc}")
        return False


def _run_backtest() -> dict | None:
    """Run backtest_parameters.py, stream output live, return parsed metrics."""
    # Use `uv run python` so the ETL venv (with pandas, yfinance, etc.) is activated
    cmd = ["uv", "run", "python", str(_BACKTEST_SCRIPT)]
    collected: list[str] = []

    try:
        with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # merge stderr into stdout
            text=True,
            bufsize=1,                 # line-buffered
            cwd=str(_ETL_ROOT),
        ) as proc:
            try:
                for raw_line in proc.stdout:
                    line = raw_line.rstrip("\n")
                    collected.append(line)
                    # Stream every line indented so it's visually nested
                    print(f"  │ {line}", flush=True)
                proc.wait()
            except KeyboardInterrupt:
                # Kill the backtest subprocess before propagating the interrupt
                _stop_requested.set()
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                raise  # let the watch loop's KeyboardInterrupt handler fire
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        _log(f"[error] backtest subprocess failed: {exc}")
        return None

    full_output = "\n".join(collected)

    # Extract code suggestions as a side-effect (read by watch loop)
    global _last_backtest_suggestions
    _last_backtest_suggestions = _extract_code_suggestions(full_output)

    metrics_match = re.search(r"---metrics---\n(.*?)---end---", full_output, re.DOTALL)
    if not metrics_match:
        _log("[error] no ---metrics--- block found in backtest output")
        return None

    metrics: dict = {}
    for line in metrics_match.group(1).strip().splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            try:
                metrics[k.strip()] = float(v.strip())
            except ValueError:
                pass

    return metrics if "profit_factor" in metrics else None


def _git_short_sha() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=str(_REPO_ROOT)
        )
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _git_commit_params(description: str) -> str:
    """Stage trading_params.py and commit it. Returns short SHA."""
    subprocess.run(
        ["git", "add", str(_PARAMS_FILE)],
        cwd=str(_REPO_ROOT), capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", f"research: {description}"],
        cwd=str(_REPO_ROOT), capture_output=True
    )
    return _git_short_sha()


_PARAMS_BACKUP = _PARAMS_FILE.with_name("trading_params.py.bak")


def _save_params_backup() -> None:
    """Save current trading_params.py to a backup before proposing changes."""
    _PARAMS_BACKUP.write_text(_PARAMS_FILE.read_text())


def _git_restore_params() -> None:
    """Revert trading_params.py to pre-proposal state.

    Uses a .bak file saved before each iteration (more reliable than git checkout
    since trading_params.py may not be committed to the git index yet).
    """
    if _PARAMS_BACKUP.exists():
        _PARAMS_FILE.write_text(_PARAMS_BACKUP.read_text())
        return
    # Fallback: git checkout (only works if file is tracked)
    subprocess.run(
        ["git", "checkout", "--", str(_PARAMS_FILE.relative_to(_REPO_ROOT))],
        cwd=str(_REPO_ROOT), capture_output=True
    )


def _ensure_results_file() -> None:
    if not _RESULTS_FILE.exists():
        with open(_RESULTS_FILE, "w", newline="") as f:
            csv.writer(f, delimiter="\t").writerow(RESULTS_HEADER)


def _append_result(row: dict) -> None:
    _ensure_results_file()
    with open(_RESULTS_FILE, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RESULTS_HEADER, delimiter="\t")
        w.writerow(row)


def _load_results() -> list[dict]:
    if not _RESULTS_FILE.exists():
        return []
    with open(_RESULTS_FILE, newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _build_prompt(current_params: str, current_pf: float, history: list[dict], program: str) -> str:
    """Build the full LLM prompt (for claude-cli / anthropic providers)."""
    history_lines = []
    for row in history[-10:]:
        status = "✓ kept" if row["status"] == "keep" else "✗ discarded"
        history_lines.append(
            f"  {row['iteration']:>3}. pf={float(row['profit_factor']):.3f}  {status}  {row['description']}"
        )
    history_text = "\n".join(history_lines) if history_lines else "  (no history yet — this is the first experiment)"

    return f"""You are optimizing a quantitative trading system's exit parameters.

## Research Program
{program}

## Current Parameters (trading_params.py)
```python
{current_params}
```

## Current Metric
profit_factor = {current_pf:.4f}  (baseline; higher is better; target > 1.0)

## Experiment History
{history_text}

Propose ONE parameter change to improve profit_factor.
Do not repeat a change that was already tried (see history).
Follow the response format from the Research Program exactly."""


def _parse_param_values(params_text: str) -> dict[str, str]:
    """Extract {PARAM_NAME: value_str} from a trading_params.py text block."""
    result: dict[str, str] = {}
    for line in params_text.splitlines():
        m = re.match(r"([A-Z_]+)\s*(?::\s*\w+)?\s*=\s*(.+?)(?:\s*#.*)?$", line.strip())
        if m:
            result[m.group(1)] = m.group(2).strip()
    return result


def _extract_target_param(description: str) -> str | None:
    """Heuristic: find which UPPER_SNAKE_CASE param name the description mentions."""
    m = re.search(r'\b([A-Z][A-Z0-9_]{3,})\b', description)
    return m.group(1) if m else None


def _build_ollama_messages(
    current_params: str,
    current_pf: float,
    history: list[dict],
    tried_values: dict[str, set] | None = None,
) -> list[dict]:
    """Build a compact chat-API message list for small Ollama models.

    Uses /api/chat (system + user roles) rather than /api/generate, and strips
    parameter file comments to keep the prompt well within phi4-mini's context window.
    """
    # Keep assignment lines with type annotations intact; strip block comments and docstrings
    compact_params_lines = []
    in_docstring = False
    for line in current_params.splitlines():
        stripped = line.strip()
        if stripped.startswith('"""'):
            in_docstring = not in_docstring
            continue
        if in_docstring or not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            compact_params_lines.append(stripped)  # preserves "ATR_PERIOD: int = 20"
    compact_params = "\n".join(compact_params_lines)

    history_lines = []
    for row in history[-6:]:
        status = "kept" if row["status"] == "keep" else "disc"
        history_lines.append(
            f"  {row['iteration']:>3}. pf={float(row['profit_factor']):.3f} {status}: {row['description']}"
        )
    history_text = "\n".join(history_lines) if history_lines else "  (none yet)"

    system_msg = (
        "You optimize quantitative trading parameters. "
        "Respond ONLY in this exact format — no other text:\n\n"
        "DESCRIPTION: <one-line description of the single change>\n"
        "REASON: <2-3 sentences why this should improve profit_factor>\n"
        "---PARAMS---\n"
        "<full trading_params.py content with your single change applied>\n"
        "---END---"
    )

    # Build "already tried" section so the model avoids repeating exact values
    tried_text = ""
    if tried_values:
        tried_lines = []
        for param, vals in sorted(tried_values.items()):
            if vals:
                tried_lines.append(f"  {param}: {', '.join(sorted(vals))}")
        if tried_lines:
            tried_text = "\nAlready tried — do NOT propose these exact values again:\n" + "\n".join(tried_lines) + "\n"

    user_msg = f"""Current trading_params.py (current values):
{compact_params}

Current score: profit_factor={current_pf:.4f} (target above 1.0, higher is better)

Valid ranges:
  ATR_PERIOD [10,30]  ATR_MULTIPLIER [1.0,3.0]  TRAILING_STOP_PCT [0.10,0.35]
  TRAILING_ARM_PCT [0.03,0.10]  TIME_EXIT_DAYS [30,90]  MIN_SIGNAL_CONFIDENCE [0.50,0.80]

WARNING: Do NOT change MIN_SIGNAL_CONFIDENCE above 0.70. Higher values are counterproductive.
{tried_text}
Recent trials:
{history_text}

Output the COMPLETE updated trading_params.py between ---PARAMS--- and ---END---.
CRITICAL: preserve type annotations exactly as shown (e.g. ATR_PERIOD: int = 20, not ATR_PERIOD = 20).
Only Python assignments and comments. No other text inside that block."""

    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]


def _parse_llm_response(response: str) -> tuple[str, str] | None:
    """Parse DESCRIPTION + params block from an LLM response.

    Accepts several format variants that small models produce:
      ---PARAMS---\\n<content>\\n---END---   (canonical)
      ---\\nPARAMS:\\n<content>\\n---END---  (phi4-mini variant)
      ```python\\n<content>\\n```            (markdown code-block fallback)
    """
    desc_match = re.search(r"DESCRIPTION:\s*(.+)", response)

    # 1. Canonical: ---PARAMS---...(---END--- or end-of-string)
    params_match = re.search(
        r"---PARAMS---\s*\n(.*?)(?:---END---|$)", response, re.DOTALL | re.IGNORECASE
    )

    # 2. phi4-mini variant: ---\nPARAMS:\n<content>\n---END---  (or end-of-string)
    if not params_match:
        params_match = re.search(
            r"---\s*\n\s*PARAMS:?\s*\n(.*?)(?:---END---|---\s*$|$)",
            response, re.DOTALL | re.IGNORECASE
        )

    # 3. Markdown code fence: ```python ... ```
    if not params_match:
        params_match = re.search(
            r"```(?:python)?\s*\n(.*?)```", response, re.DOTALL
        )

    if not desc_match:
        logger.error("Could not parse LLM response (missing DESCRIPTION):\n%s", response[:300])
        return None
    if not params_match:
        logger.error("Could not parse LLM response (missing ---PARAMS--- block):\n%s", response[:300])
        return None

    params_content = params_match.group(1).strip()
    # Strip any stray markdown fences that crept inside the block
    params_content = re.sub(r"^```python\s*\n?", "", params_content)
    params_content = re.sub(r"\n?```\s*$", "", params_content)

    # Pre-clean: strip plain-text lines that models sometimes hallucinate into the block
    # e.g. "METRIC TO OPTIMIZE: profit_factor (...)" — colon-separated prose without '='
    clean_lines = []
    for line in params_content.splitlines():
        stripped = line.strip()
        # Keep blank lines, comments, docstring markers, and lines with '='
        if not stripped or stripped.startswith("#") or '"""' in stripped or "=" in stripped:
            clean_lines.append(line)
        # Also keep 'pass', 'import', etc. (valid Python without '=')
        elif re.match(r"^(pass|import|from|class|def)\b", stripped):
            clean_lines.append(line)
        # Everything else (plain prose like "METRIC TO OPTIMIZE: ...") — drop it
    params_content = "\n".join(clean_lines).strip()

    # Sanity-check 1: must contain the expected parameter names
    if "ATR_PERIOD" not in params_content or "=" not in params_content:
        logger.error(
            "Could not parse LLM response (params block missing ATR_PERIOD — likely truncated):\n%s",
            response[:300],
        )
        return None

    # Sanity-check 2: must be valid Python after prose-line stripping
    try:
        compile(params_content, "<trading_params>", "exec")
    except SyntaxError as exc:
        logger.error(
            "Could not parse LLM response (params block is not valid Python — %s):\n%s",
            exc, params_content[:300],
        )
        return None

    return desc_match.group(1).strip(), params_content


def _ask_llm(
    current_params: str,
    current_pf: float,
    history: list[dict],
    program: str,
    provider: str = "claude-cli",
    ollama_model: str = "phi4-mini",
    tried_values: dict[str, set] | None = None,
) -> tuple[str, str] | None:
    """Ask an LLM to propose ONE parameter change.

    Providers:
      claude-cli  — calls `claude -p` subprocess (uses existing Claude Code session)
      ollama      — calls local Ollama HTTP API (no API key needed)
      anthropic   — calls Anthropic API directly (requires ANTHROPIC_API_KEY env var)

    Returns (description, new_params_content) or None on failure.
    """
    prompt = _build_prompt(current_params, current_pf, history, program)

    if provider == "claude-cli":
        try:
            # Unset CLAUDECODE so the subprocess isn't blocked by the nested-session guard
            env = os.environ.copy()
            env.pop("CLAUDECODE", None)
            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True, text=True, timeout=180, env=env,
            )
            if result.returncode != 0:
                logger.error("claude CLI exited %d: %s", result.returncode, result.stderr[:300])
                return None
            response = result.stdout
        except KeyboardInterrupt:
            raise
        except FileNotFoundError:
            logger.error("claude CLI not found. Install Claude Code or use --provider ollama")
            return None
        except subprocess.TimeoutExpired:
            logger.error("claude CLI timed out after 120s")
            return None
        except Exception as exc:
            logger.error("claude CLI call failed: %s", exc)
            return None

    elif provider == "ollama":
        import urllib.request
        import json as _json
        try:
            # Use /api/chat (system+user roles) — far more reliable for small models
            messages = _build_ollama_messages(current_params, current_pf, history, tried_values=tried_values)
            body = _json.dumps({
                "model": ollama_model,
                "messages": messages,
                "stream": True,
                "options": {"temperature": 0.7, "num_predict": 4096},
            }).encode()
            req = urllib.request.Request(
                "http://localhost:11434/api/chat",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            response_parts: list[str] = []
            print(f"  ◈ [{ollama_model}] ", end="", flush=True)
            with urllib.request.urlopen(req, timeout=180) as resp:
                for raw_line in resp:
                    chunk = _json.loads(raw_line)
                    # /api/chat returns {"message": {"content": "..."}} per chunk
                    token = chunk.get("message", {}).get("content", "")
                    response_parts.append(token)
                    print(token, end="", flush=True)
                    if chunk.get("done"):
                        break
            print(flush=True)  # newline after stream ends
            response = "".join(response_parts)
        except KeyboardInterrupt:
            print(flush=True)
            raise
        except Exception as exc:
            print(flush=True)
            logger.error("Ollama API call failed: %s", exc)
            return None

    elif provider == "anthropic":
        try:
            client = anthropic.Anthropic()
            message = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            response = message.content[0].text
        except Exception as exc:
            logger.error("Anthropic API call failed: %s", exc)
            return None

    else:
        logger.error("Unknown provider: %s", provider)
        return None

    return _parse_llm_response(response)


def _ask_llm_with_retry(
    current_params: str,
    current_pf: float,
    history: list[dict],
    program: str,
    provider: str = "claude-cli",
    ollama_model: str = "phi4-mini",
    max_retries: int = 3,
    tried_values: dict[str, set] | None = None,
) -> tuple[str, str] | None:
    """Wrapper around _ask_llm that retries up to max_retries times on parse failure."""
    for attempt in range(max_retries):
        result = _ask_llm(
            current_params, current_pf, history, program, provider, ollama_model,
            tried_values=tried_values,
        )
        if result is not None:
            return result
        if attempt < max_retries - 1:
            _log(f"[retry {attempt + 1}/{max_retries - 1}] LLM parse failed — retrying...")
    return None


# ──────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────

@click.group()
def cli():
    """Autonomous trading parameter research — autoresearch-style."""


@cli.command()
@click.option("--iterations", "-n", default=10, show_default=True,
              help="Number of research iterations to run.")
@click.option("--metric", default="profit_factor",
              type=click.Choice(["profit_factor", "ev_per_trade", "win_rate"]),
              show_default=True, help="Metric to optimize.")
@click.option("--baseline-only", is_flag=True,
              help="Run baseline backtest only, no iteration.")
@click.option("--provider", default="claude-cli",
              type=click.Choice(["claude-cli", "ollama", "anthropic"]),
              show_default=True, help="LLM backend (claude-cli=local session, ollama=local model).")
@click.option("--ollama-model", default="phi4-mini", show_default=True,
              help="Ollama model to use when --provider=ollama.")
def run(iterations: int, metric: str, baseline_only: bool, provider: str, ollama_model: str) -> None:

    """Run the autonomous parameter research loop."""
    # Validate files
    for path, label in [(_PARAMS_FILE, "trading_params.py"),
                        (_BACKTEST_SCRIPT, "backtest_parameters.py"),
                        (_PROGRAM_FILE, "research_program.md")]:
        if not path.exists():
            click.echo(f"[error] {label} not found at {path}", err=True)
            raise SystemExit(1)

    _ensure_results_file()
    program = _PROGRAM_FILE.read_text()

    # ── Baseline run ──────────────────────────────────────────────
    click.echo("\n" + "=" * 62)
    click.echo("TRADING RESEARCH — BASELINE RUN")
    click.echo("=" * 62)
    click.echo(f"  Params file : {_PARAMS_FILE.relative_to(_REPO_ROOT)}")
    click.echo(f"  Metric      : {metric}")
    click.echo(f"  Iterations  : {iterations}")
    click.echo()

    click.echo("Running baseline backtest...")
    baseline_metrics = _run_backtest()
    if baseline_metrics is None:
        click.echo("[error] Baseline backtest failed.", err=True)
        raise SystemExit(1)

    best_pf = baseline_metrics["profit_factor"]
    click.echo(f"  profit_factor = {best_pf:.4f}")
    click.echo(f"  ev_per_trade  = {baseline_metrics['ev_per_trade']:+.4f}")
    click.echo(f"  win_rate      = {baseline_metrics['win_rate']:.1%}")
    click.echo(f"  n_simulated   = {int(baseline_metrics.get('n_simulated', 0))}")

    # Record baseline
    history = _load_results()
    if not history:  # only record baseline once
        _append_result({
            "timestamp": datetime.utcnow().isoformat(),
            "iteration": 0,
            "profit_factor": f"{baseline_metrics['profit_factor']:.6f}",
            "ev_per_trade": f"{baseline_metrics['ev_per_trade']:.6f}",
            "win_rate": f"{baseline_metrics['win_rate']:.6f}",
            "n": int(baseline_metrics.get("n_simulated", 0)),
            "status": "baseline",
            "description": "baseline (initial params)",
        })
        history = _load_results()

    if baseline_only:
        return

    # ── Research loop ─────────────────────────────────────────────
    click.echo(f"\nStarting {iterations} research iterations...\n")

    kept = 0
    discarded = 0
    metric_key = metric  # profit_factor | ev_per_trade | win_rate

    for i in range(1, iterations + 1):
        click.echo(f"{'─' * 62}")
        click.echo(f"  Iteration {i}/{iterations}  |  best {metric_key} = {best_pf:.4f}")
        click.echo(f"{'─' * 62}")

        current_params = _PARAMS_FILE.read_text()

        # Ask LLM to propose a change
        click.echo(f"  → Asking {provider} for a parameter change...")
        result = _ask_llm_with_retry(current_params, best_pf, history, program, provider=provider, ollama_model=ollama_model)
        if result is None:
            click.echo(f"  [skip] {provider} returned unusable response after retries.")
            continue

        description, new_params = result
        click.echo(f"  → Proposed: {description}")

        # Backup current params before applying change (enables reliable restore)
        _save_params_backup()
        _PARAMS_FILE.write_text(new_params)

        # Run backtest
        click.echo("  → Running backtest...")
        metrics = _run_backtest()
        if metrics is None:
            click.echo("  [crash] Backtest failed — restoring params.")
            _git_restore_params()
            _append_result({
                "timestamp": datetime.utcnow().isoformat(),
                "iteration": i,
                "profit_factor": "0",
                "ev_per_trade": "0",
                "win_rate": "0",
                "n": 0,
                "status": "crash",
                "description": description,
            })
            history = _load_results()
            discarded += 1
            continue

        new_pf = metrics[metric_key]
        pf_delta = new_pf - best_pf

        click.echo(f"  → profit_factor = {metrics['profit_factor']:.4f}  ({pf_delta:+.4f})")
        click.echo(f"     ev_per_trade  = {metrics['ev_per_trade']:+.4f}")
        click.echo(f"     win_rate      = {metrics['win_rate']:.1%}")

        if new_pf > best_pf:
            # Keep: commit the change
            sha = _git_commit_params(description)
            click.echo(f"  ✓ KEPT  (commit {sha})")
            best_pf = new_pf
            status = "keep"
            kept += 1
        else:
            # Discard: restore params
            _git_restore_params()
            click.echo("  ✗ DISCARDED")
            status = "discard"
            discarded += 1

        _append_result({
            "timestamp": datetime.utcnow().isoformat(),
            "iteration": i,
            "profit_factor": f"{metrics['profit_factor']:.6f}",
            "ev_per_trade": f"{metrics['ev_per_trade']:.6f}",
            "win_rate": f"{metrics['win_rate']:.6f}",
            "n": int(metrics.get("n_simulated", 0)),
            "status": status,
            "description": description,
        })
        history = _load_results()

    # ── Summary ───────────────────────────────────────────────────
    click.echo("\n" + "=" * 62)
    click.echo("RESEARCH COMPLETE")
    click.echo("=" * 62)
    click.echo(f"  Iterations   : {iterations}")
    click.echo(f"  Kept         : {kept}")
    click.echo(f"  Discarded    : {discarded}")
    click.echo(f"  Best {metric_key:<15}: {best_pf:.4f}")
    click.echo(f"  Baseline     : {baseline_metrics['profit_factor']:.4f}")
    click.echo(f"  Improvement  : {best_pf - baseline_metrics['profit_factor']:+.4f}")
    click.echo(f"\n  Results log  : {_RESULTS_FILE}")
    click.echo(f"  Current best : {_PARAMS_FILE}")


@cli.command()
def status() -> None:
    """Show research results history."""
    rows = _load_results()
    if not rows:
        click.echo("No results yet. Run: mcli run trading research run")
        return

    click.echo(f"\n{'Iter':>4}  {'PF':>8}  {'EV':>9}  {'WR':>7}  {'Status':>9}  Description")
    click.echo("─" * 80)
    for row in rows:
        status_icon = {"keep": "✓", "discard": "✗", "baseline": "○", "crash": "💥"}.get(row["status"], "?")
        click.echo(
            f"  {row['iteration']:>3}  "
            f"{float(row['profit_factor']):>8.4f}  "
            f"{float(row['ev_per_trade']):>+9.4f}  "
            f"{float(row['win_rate']):>7.1%}  "
            f"{status_icon} {row['status']:<8}  "
            f"{row['description']}"
        )

    kept = [r for r in rows if r["status"] == "keep"]
    if kept:
        best = max(kept, key=lambda r: float(r["profit_factor"]))
        click.echo(f"\nBest kept: pf={float(best['profit_factor']):.4f}  — \"{best['description']}\"")


@cli.command()
def params() -> None:
    """Show current trading_params.py."""
    if not _PARAMS_FILE.exists():
        click.echo(f"[error] {_PARAMS_FILE} not found", err=True)
        return
    click.echo(_PARAMS_FILE.read_text())


# ──────────────────────────────────────────────────────────────────
# promote: push research findings into production config
# ──────────────────────────────────────────────────────────────────

_EDGE_FN_FILE = _REPO_ROOT / "supabase" / "functions" / "reference-portfolio" / "index.ts"

# Maps trading_params.py var → reference_portfolio_config column
# Values in trading_params.py are fractions (0.20); the DB stores percentages (20.00)
_PARAM_TO_CONFIG: list[tuple[str, str, float]] = [
    # (params_var, db_column, scale_factor)
    ("TRAILING_STOP_PCT",      "trailing_stop_pct",          100.0),  # 0.20 → 20.00
    ("TIME_EXIT_DAYS",         "max_hold_days",                 1.0),  # 60   → 60
    ("MIN_POSITION_PCT",       "base_position_size_pct",      100.0),  # 0.01 → 1.00
    ("MAX_POSITION_PCT",       "max_position_size_pct",       100.0),  # 0.05 → 5.00
    ("MIN_SIGNAL_CONFIDENCE",  "min_confidence_threshold",      1.0),  # 0.70 → 0.70
]


def _load_trading_params() -> dict:
    """Load trading_params.py and return a dict of its variables."""
    import importlib.util as ilu
    spec = ilu.spec_from_file_location("trading_params", str(_PARAMS_FILE))
    mod = ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {k: getattr(mod, k) for k in dir(mod) if k.isupper()}


def _supabase_creds() -> tuple[str, str]:
    """Load SUPABASE_URL and SUPABASE_SERVICE_KEY from .env."""
    from dotenv import dotenv_values
    env = dotenv_values(str(_REPO_ROOT / ".env"))
    url = env.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL", "")
    key = env.get("SUPABASE_SERVICE_KEY") or env.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY", "")
    return url, key


def _fetch_current_config() -> dict | None:
    """Fetch the current reference_portfolio_config row from Supabase REST API."""
    import httpx
    url, key = _supabase_creds()
    if not url or not key:
        logger.error("SUPABASE_URL or SUPABASE_SERVICE_KEY not found in .env")
        return None
    try:
        r = httpx.get(
            f"{url}/rest/v1/reference_portfolio_config",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            params={"select": "*", "limit": "1"},
            timeout=10,
        )
        r.raise_for_status()
        rows = r.json()
        return rows[0] if rows else None
    except Exception as exc:
        logger.error("Failed to fetch config: %s", exc)
        return None


def _update_config(updates: dict, row_id: int | None = None) -> bool:
    """Update reference_portfolio_config via Supabase REST API (singleton row).

    PostgREST PATCH requires an explicit row filter — ?limit=1 is not valid.
    We filter by the row's primary key if provided, otherwise fetch it first.
    """
    import httpx
    url, key = _supabase_creds()
    if not url or not key:
        return False

    if row_id is None:
        live = _fetch_current_config()
        if live is None:
            return False
        row_id = live.get("id")
        if row_id is None:
            logger.error("reference_portfolio_config row has no 'id' field — cannot PATCH")
            return False

    try:
        r = httpx.patch(
            f"{url}/rest/v1/reference_portfolio_config",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            params={"id": f"eq.{row_id}"},
            json=updates,
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as exc:
        logger.error("Failed to update config: %s", exc)
        return False


def _patch_atr_multiplier(new_multiplier: float) -> bool:
    """Patch the hardcoded ATR multiplier in the edge function source."""
    import re as _re
    if not _EDGE_FN_FILE.exists():
        logger.error("Edge function not found at %s", _EDGE_FN_FILE)
        return False
    src = _EDGE_FN_FILE.read_text()
    # Pattern: currentPrice - (1.5 * atr)  →  currentPrice - (X.X * atr)
    pattern = r"(currentPrice - \()\d+\.?\d*( \* atr\))"
    replacement = rf"\g<1>{new_multiplier}\g<2>"
    new_src, n = _re.subn(pattern, replacement, src)
    if n == 0:
        logger.warning("ATR multiplier pattern not found in edge function source")
        return False
    _EDGE_FN_FILE.write_text(new_src)
    return True


def _perform_promote(silent: bool = False) -> tuple[bool, bool]:
    """Core promote logic shared by `promote` and `watch`.

    Returns (success, atr_changed).
    atr_changed=True means the edge function source was patched and needs deploy.
    """
    try:
        rp = _load_trading_params()
    except Exception as exc:
        logger.error("Could not load trading_params.py: %s", exc)
        return False, False

    live = _fetch_current_config()
    if live is None:
        return False, False

    db_updates: dict = {}
    current_atr = 1.5
    new_atr = rp.get("ATR_MULTIPLIER", 1.5)
    atr_changed = abs(new_atr - current_atr) > 1e-6

    for var, col, scale in _PARAM_TO_CONFIG:
        new_val = rp.get(var)
        if new_val is None:
            continue
        new_db_val = round(new_val * scale, 4)
        cur_db_val = live.get(col)
        if cur_db_val is None:
            continue
        if abs(new_db_val - float(cur_db_val)) > 1e-6:
            db_updates[col] = new_db_val

    if not db_updates and not atr_changed:
        if not silent:
            click.echo("  No changes — production already matches trading_params.py.")
        return True, False  # success but nothing to do

    if db_updates:
        if not _update_config(db_updates, row_id=live.get("id")):
            return False, False
        if not silent:
            click.echo(f"  ✓ Config updated ({', '.join(db_updates.keys())})")

    if atr_changed:
        if _patch_atr_multiplier(new_atr):
            if not silent:
                click.echo(f"  ✓ ATR multiplier patched: {current_atr} → {new_atr}")
        else:
            logger.warning("Could not patch ATR multiplier in edge function")

    return True, atr_changed


def _deploy_edge_function() -> bool:
    """Run supabase functions deploy reference-portfolio. Returns True on success."""
    click.echo("  → Deploying edge function...")
    result = subprocess.run(
        ["supabase", "functions", "deploy", "reference-portfolio"],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        click.echo("  ✓ Edge function deployed.")
        return True
    else:
        click.echo(f"  [warn] Deploy failed (rc={result.returncode}): {result.stderr.strip()[:200]}")
        return False


@cli.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
@click.option("--dry-run", is_flag=True, help="Show what would change without applying.")
def promote(yes: bool, dry_run: bool) -> None:
    """Push the current trading_params.py into production config.

    Updates the reference_portfolio_config Supabase table (hot-reload, no
    redeploy needed) and patches the ATR multiplier in the edge function source
    if it changed (requires supabase functions deploy after).
    """
    if not _PARAMS_FILE.exists():
        click.echo("[error] trading_params.py not found — run the research loop first.", err=True)
        raise SystemExit(1)

    try:
        rp = _load_trading_params()
    except Exception as exc:
        click.echo(f"[error] Could not load trading_params.py: {exc}", err=True)
        raise SystemExit(1)

    click.echo("Fetching current reference_portfolio_config...")
    live = _fetch_current_config()
    if live is None:
        click.echo("[error] Could not fetch live config from Supabase.", err=True)
        raise SystemExit(1)

    # ── Build and print diff ──────────────────────────────────────
    db_updates: dict = {}
    current_atr = 1.5
    new_atr = rp.get("ATR_MULTIPLIER", 1.5)
    atr_changed = abs(new_atr - current_atr) > 1e-6

    click.echo("\n" + "=" * 62)
    click.echo("PROMOTE: trading_params.py → production config")
    click.echo("=" * 62)
    click.echo(f"\n  {'Parameter':<28} {'Current':>12} {'New':>12}  {'Change'}")
    click.echo(f"  {'─'*28} {'─'*12} {'─'*12}  {'─'*10}")

    any_change = False
    for var, col, scale in _PARAM_TO_CONFIG:
        new_val = rp.get(var)
        if new_val is None:
            continue
        new_db_val = round(new_val * scale, 4)
        cur_db_val = live.get(col)
        if cur_db_val is None:
            continue
        cur_db_val = float(cur_db_val)
        changed = abs(new_db_val - cur_db_val) > 1e-6
        marker = "●" if changed else " "
        delta_str = f"{new_db_val - cur_db_val:+.2f}" if changed else "(unchanged)"
        click.echo(f"  {marker} {col:<28} {cur_db_val:>12.2f} {new_db_val:>12.2f}  {delta_str}")
        if changed:
            db_updates[col] = new_db_val
            any_change = True

    marker = "●" if atr_changed else " "
    delta_str = f"{new_atr - current_atr:+.2f}" if atr_changed else "(unchanged)"
    click.echo(f"  {marker} {'ATR_MULTIPLIER (edge fn)':<28} {current_atr:>12.2f} {new_atr:>12.2f}  {delta_str}")
    if atr_changed:
        any_change = True

    if not any_change:
        click.echo("\n  No changes — production already matches trading_params.py.")
        return

    if atr_changed:
        click.echo("\n  ⚠  ATR_MULTIPLIER requires edge function redeploy after promote.")

    if dry_run:
        click.echo("\n  [dry-run] No changes applied.")
        return

    if not yes:
        click.echo()
        if not click.confirm("  Apply these changes to production?", default=False):
            click.echo("  Aborted.")
            return

    success, fn_patched = _perform_promote(silent=False)
    if not success:
        click.echo("  [error] Promote failed.", err=True)
        raise SystemExit(1)

    click.echo("\n  ✓ Promote complete. Config changes are live immediately.")
    if fn_patched:
        click.echo("    ATR multiplier change requires: supabase functions deploy reference-portfolio")


@cli.command()
@click.option("-t", "--threshold", default=0.5, show_default=True, type=float,
              help="Auto-promote when profit_factor reaches this value.")
@click.option("--deploy/--no-deploy", "auto_deploy", default=True, show_default=True,
              help="Auto-deploy edge function after promote if ATR_MULTIPLIER changed.")
@click.option("--metric", default="profit_factor",
              type=click.Choice(["profit_factor", "ev_per_trade", "win_rate"]),
              show_default=True, help="Metric to optimize.")
@click.option("--provider", default="claude-cli",
              type=click.Choice(["claude-cli", "ollama", "anthropic"]),
              show_default=True, help="LLM backend (claude-cli=local session, ollama=local model).")
@click.option("--ollama-models", default="phi4-mini", show_default=True,
              help="Comma-separated Ollama models to round-robin through (e.g. phi4-mini,qwen2.5-coder:7b-instruct,mistral:instruct).")
@click.option("--stall-limit", default=25, show_default=True, type=int,
              help="Consecutive bad outcomes before rotating to the next model.")
def watch(threshold: float, auto_deploy: bool, metric: str, provider: str,
          ollama_models: str, stall_limit: int) -> None:
    """Run indefinitely. Auto-promotes and deploys when threshold is reached.

    Loops until Ctrl+C or true diminishing returns (all models exhausted one
    full rotation without any improvement). Each improvement above --threshold
    triggers an immediate promote + optional edge function redeploy.

    Round-robin (--provider ollama only): after --stall-limit consecutive bad
    outcomes (skips + discards), rotates to the next model in --ollama-models.
    After a full rotation with zero improvements, the loop terminates.

    Examples:
        mcli run trading_research watch -t 0.8 --provider ollama
        mcli run trading_research watch --provider ollama \\
            --ollama-models phi4-mini,qwen2.5-coder:7b-instruct,mistral:instruct
        mcli run trading_research watch -t 0.8 --no-deploy
    """
    for path, label in [(_PARAMS_FILE, "trading_params.py"),
                        (_BACKTEST_SCRIPT, "backtest_parameters.py"),
                        (_PROGRAM_FILE, "research_program.md")]:
        if not path.exists():
            click.echo(f"[error] {label} not found at {path}", err=True)
            raise SystemExit(1)

    _ensure_results_file()
    program = _PROGRAM_FILE.read_text()
    metric_key = metric

    # ── Round-robin model list (ollama only) ──────────────────────
    model_list = [m.strip() for m in ollama_models.split(",") if m.strip()]
    model_idx = 0
    active_model = model_list[model_idx]
    consecutive_bad = 0      # skips + discards in a row for current model
    keeps_this_rotation = 0  # improvements found in the current full rotation

    # ── Baseline ──────────────────────────────────────────────────
    print("\n" + "=" * 62, flush=True)
    print(f"TRADING RESEARCH WATCH  |  threshold={threshold}  metric={metric}", flush=True)
    if provider == "ollama":
        print(f"  Models: {' → '.join(model_list)}  (rotate after {stall_limit} bad outcomes)", flush=True)
    print("=" * 62, flush=True)
    _log("Running baseline backtest...")
    baseline_metrics = _run_backtest()
    if baseline_metrics is None:
        _log("[error] Baseline backtest failed.")
        raise SystemExit(1)

    best_pf = baseline_metrics[metric_key]
    last_promoted_pf = best_pf
    _log(f"Baseline  profit_factor={best_pf:.4f}  ev={baseline_metrics['ev_per_trade']:+.4f}  wr={baseline_metrics['win_rate']:.1%}")
    _log(f"Threshold={threshold:.4f}  auto_deploy={auto_deploy}  Ctrl+C or 'q'+Enter to stop")
    _start_quit_listener()

    history = _load_results()
    if not history:
        _append_result({
            "timestamp": datetime.utcnow().isoformat(),
            "iteration": 0,
            "profit_factor": f"{baseline_metrics['profit_factor']:.6f}",
            "ev_per_trade": f"{baseline_metrics['ev_per_trade']:.6f}",
            "win_rate": f"{baseline_metrics['win_rate']:.6f}",
            "n": int(baseline_metrics.get("n_simulated", 0)),
            "status": "baseline",
            "description": "baseline (initial params)",
        })
        history = _load_results()

    total_kept = 0
    total_discarded = 0
    total_promoted = 0
    i = 0
    stall_terminated = False

    code_agent_run = False  # only spawn the agent once per watch session
    tried_values: dict[str, set] = {}  # PARAM_NAME → set of string values tried this session

    def _maybe_rotate_model() -> None:
        """Rotate to the next Ollama model after stall_limit consecutive bad outcomes.

        On a full rotation with no improvement:
          - First time: spawn the code implementation agent (if suggestions exist), then
            re-run the baseline and reset so the loop continues with fresh code.
          - Second time (or if no suggestions): terminate — true diminishing returns.
        """
        nonlocal model_idx, active_model, consecutive_bad, keeps_this_rotation
        nonlocal stall_terminated, best_pf, last_promoted_pf, code_agent_run
        if provider != "ollama":
            return
        if consecutive_bad < stall_limit:
            return

        # Single-model case: stall termination without rotation
        if len(model_list) <= 1:
            _log("=" * 55)
            _log(f"STALL DETECTED — {active_model} exhausted {stall_limit} consecutive bad outcomes.")
            _log("Single-model run: no rotation possible. Terminating loop.")
            stall_terminated = True
            return

        next_idx = (model_idx + 1) % len(model_list)
        completing_rotation = (next_idx == 0)

        if completing_rotation:
            if keeps_this_rotation == 0:
                # All models exhausted with no improvement this rotation.
                if _last_backtest_suggestions and not code_agent_run:
                    # First stall — try spawning the code agent.
                    code_agent_run = True
                    success = _spawn_implementation_agent(
                        _last_backtest_suggestions,
                        provider=provider,
                        ollama_model=active_model,
                    )
                    if success:
                        _log("Re-running baseline with updated code...")
                        new_baseline = _run_backtest()
                        if new_baseline:
                            best_pf = new_baseline[metric_key]
                            last_promoted_pf = min(last_promoted_pf, best_pf)
                            _log(f"New baseline after agent changes: pf={best_pf:.4f}")
                    # Reset rotation state so the loop continues fresh.
                    keeps_this_rotation = 0
                    model_idx = 0
                    active_model = model_list[0]
                    consecutive_bad = 0
                    _log(f"Resuming from model 1/{len(model_list)}: {active_model}")
                    return
                else:
                    _log("=" * 55)
                    _log("STALL DETECTED — true diminishing returns reached.")
                    _log(f"All {len(model_list)} model(s) exhausted {stall_limit} consecutive bad")
                    _log("outcomes each with zero improvements this rotation.")
                    if code_agent_run:
                        _log("Code agent already ran — no further improvements possible.")
                    _log("Terminating loop.")
                    stall_terminated = True
                    return
            else:
                _log(f"Rotation complete ({keeps_this_rotation} improvement(s) found). Starting next rotation.")
                keeps_this_rotation = 0

        model_idx = next_idx
        active_model = model_list[model_idx]
        consecutive_bad = 0
        _log(f"MODEL ROTATE → {active_model}  ({model_idx + 1}/{len(model_list)})")

    try:
        while True:
            if _stop_requested.is_set():
                raise KeyboardInterrupt

            i += 1
            print(flush=True)
            _log(f"{'━' * 55}")
            model_label = f"  model={active_model}" if provider == "ollama" else ""
            _log(f"Iteration #{i}  best={best_pf:.4f}  last_promoted={last_promoted_pf:.4f}{model_label}")
            _log(f"{'━' * 55}")

            current_params = _PARAMS_FILE.read_text()

            _log(f"Asking {provider} ({active_model if provider == 'ollama' else provider}) for a parameter change...")
            result = _ask_llm_with_retry(
                current_params, best_pf, history, program,
                provider=provider, ollama_model=active_model,
                tried_values=tried_values,
            )

            if result is None:
                _log(f"[skip] {active_model if provider == 'ollama' else provider} returned unusable response after retries.")
                consecutive_bad += 1
                _maybe_rotate_model()
                continue

            description, new_params = result

            # No-op check: skip if the proposed params are identical to current
            proposed_vals = _parse_param_values(new_params)
            current_vals = _parse_param_values(current_params)
            if proposed_vals == current_vals:
                _log("[skip] Proposed params identical to current — no actual change. Skipping.")
                # Add the target param's current value to tried_values so the model
                # doesn't keep proposing the same no-op (e.g. proposing 0.07 when
                # the file is already at 0.07, hallucinating the "old" value from history)
                target = _extract_target_param(description)
                if target and target in current_vals:
                    tried_values.setdefault(target, set()).add(current_vals[target])
                else:
                    # Fallback: mark all current values as tried to break the loop
                    for pn, pv in current_vals.items():
                        tried_values.setdefault(pn, set()).add(pv)
                consecutive_bad += 1
                _maybe_rotate_model()
                continue

            # Code-side hard rejection: if EVERY changed param's proposed value was
            # already tried in this session, skip without running the backtest.
            # This catches models that ignore the "Already tried" prompt section.
            changed_params = {k: v for k, v in proposed_vals.items() if v != current_vals.get(k)}
            already_tried_changes = {
                k: v for k, v in changed_params.items()
                if tried_values.get(k) and v in tried_values[k]
            }
            if changed_params and changed_params == already_tried_changes:
                param_info = ", ".join(f"{k}={v}" for k, v in already_tried_changes.items())
                _log(f"[skip] All proposed changes already tried this session ({param_info}). Skipping.")
                consecutive_bad += 1
                _maybe_rotate_model()
                continue

            # ── Locked-parameter guard ─────────────────────────────────────
            # Certain parameters are historically optimal and must not change.
            # If the LLM proposes modifying any of them, strip the change and
            # restore the locked value.  If ALL changes are locked, skip.
            LOCKED_PARAMS: dict[str, str] = {
                "TRAILING_STOP_PCT": "0.12",
                "TRAILING_ARM_PCT":  "0.15",
                "TIME_EXIT_DAYS":    "35",
                "ATR_MULTIPLIER":    "1.5",
            }
            locked_violations = {k for k in changed_params if k in LOCKED_PARAMS}
            if locked_violations:
                viol_str = ", ".join(
                    f"{k}: proposed {changed_params[k]!r} (locked={LOCKED_PARAMS[k]!r})"
                    for k in sorted(locked_violations)
                )
                _log(f"[guard] Locked parameter(s) modified — {viol_str}")
                # Rebuild new_params with locked values restored
                lines = []
                for line in new_params.splitlines():
                    m = re.match(r"([A-Z_]+)\s*(?::\s*\w+)?\s*=\s*(.+?)(?:\s*#.*)?$", line.strip())
                    if m and m.group(1) in LOCKED_PARAMS:
                        param_name_ln = m.group(1)
                        locked_val = LOCKED_PARAMS[param_name_ln]
                        # Preserve type annotation if present
                        ann_match = re.match(r"([A-Z_]+)\s*:\s*(\w+)\s*=", line)
                        if ann_match:
                            type_ann = ann_match.group(2)
                            lines.append(f"{param_name_ln}: {type_ann} = {locked_val}")
                        else:
                            lines.append(f"{param_name_ln} = {locked_val}")
                    else:
                        lines.append(line)
                new_params = "\n".join(lines)
                if new_params and not new_params.endswith("\n"):
                    new_params += "\n"
                # Re-parse after restoring locked values
                proposed_vals = _parse_param_values(new_params)
                changed_params = {k: v for k, v in proposed_vals.items() if v != current_vals.get(k)}
                if not changed_params:
                    _log("[guard] No unlocked changes remain after stripping locked params — skipping.")
                    consecutive_bad += 1
                    _maybe_rotate_model()
                    continue
                _log(f"[guard] Proceeding with unlocked changes: "
                     f"{', '.join(f'{k}={v}' for k, v in changed_params.items())}")

            # Track which values were proposed (regardless of outcome) to avoid repeats
            for param_name, val_str in changed_params.items():
                tried_values.setdefault(param_name, set()).add(val_str)

            _log(f"Proposed: {description}")

            # Backup before applying so discard can restore reliably
            _save_params_backup()
            _PARAMS_FILE.write_text(new_params)

            _log("Running backtest (streaming output below)...")
            metrics = _run_backtest()
            if metrics is None:
                _log("[crash] Backtest failed — restoring params.")
                _git_restore_params()
                _append_result({
                    "timestamp": datetime.utcnow().isoformat(),
                    "iteration": i,
                    "profit_factor": "0", "ev_per_trade": "0", "win_rate": "0",
                    "n": 0, "status": "crash", "description": description,
                })
                history = _load_results()
                total_discarded += 1
                consecutive_bad += 1
                _maybe_rotate_model()
                continue

            new_pf = metrics[metric_key]
            pf_delta = new_pf - best_pf
            _log(f"Result  profit_factor={metrics['profit_factor']:.4f} ({pf_delta:+.4f})  "
                 f"ev={metrics['ev_per_trade']:+.4f}  wr={metrics['win_rate']:.1%}")

            if new_pf > best_pf:
                sha = _git_commit_params(description)
                _log(f"KEPT ✓  (commit {sha})  new best={new_pf:.4f}")
                best_pf = new_pf
                status = "keep"
                total_kept += 1
                consecutive_bad = 0
                keeps_this_rotation += 1

                # ── Auto-promote when threshold crossed ────────────
                if best_pf >= threshold and best_pf > last_promoted_pf:
                    _log(f"THRESHOLD REACHED ({best_pf:.4f} >= {threshold}) — promoting to production...")
                    success, atr_changed = _perform_promote(silent=True)
                    if success:
                        last_promoted_pf = best_pf
                        total_promoted += 1
                        _log(f"PROMOTED ✓  (#{total_promoted})  config live immediately")
                        if auto_deploy:
                            _log("Deploying edge function to Supabase...")
                            _deploy_edge_function()
                        elif atr_changed:
                            _log("ATR changed — manual deploy needed: supabase functions deploy reference-portfolio")
                    else:
                        _log("[warn] Promote failed — continuing research.")
            else:
                _git_restore_params()
                _log(f"DISCARDED ✗  ({new_pf:.4f} <= best {best_pf:.4f})")
                status = "discard"
                total_discarded += 1
                consecutive_bad += 1
                _maybe_rotate_model()

            _append_result({
                "timestamp": datetime.utcnow().isoformat(),
                "iteration": i,
                "profit_factor": f"{metrics['profit_factor']:.6f}",
                "ev_per_trade": f"{metrics['ev_per_trade']:.6f}",
                "win_rate": f"{metrics['win_rate']:.6f}",
                "n": int(metrics.get("n_simulated", 0)),
                "status": status,
                "description": description,
            })
            history = _load_results()

            if stall_terminated:
                raise KeyboardInterrupt

    except KeyboardInterrupt:
        print("\n", flush=True)
        _log("=" * 55)
        _log("WATCH STOPPED — " + ("diminishing returns" if stall_terminated else "Ctrl+C"))
        _log(f"Iterations={i}  kept={total_kept}  discarded={total_discarded}  promotes={total_promoted}")
        _log(f"Best pf={best_pf:.4f}  last promoted={last_promoted_pf:.4f}")
        _log(f"Results log: {_RESULTS_FILE}")

        # Auto-promote on exit if there are unpromoted kept improvements
        if best_pf > last_promoted_pf and total_kept > 0:
            _log(f"Unpromoted improvements detected (best={best_pf:.4f} > last_promoted={last_promoted_pf:.4f})")
            _log("Promoting best params to production on exit...")
            success, atr_changed = _perform_promote(silent=True)
            if success:
                _log("PROMOTED ✓  Supabase config updated.")
                if auto_deploy:
                    _log("Deploying edge function to Supabase...")
                    _deploy_edge_function()
                    _log("Edge function deployed ✓")
                elif atr_changed:
                    _log("ATR_MULTIPLIER changed — manual deploy needed:")
                    _log("  supabase functions deploy reference-portfolio")
            else:
                _log("[warn] Auto-promote on exit failed. Run manually:")
                _log("  mcli run trading_research promote --yes")


@cli.command()
@click.option("--lines", "-n", default=50, show_default=True, help="Number of tail lines to show on start.")
def logs(lines: int) -> None:
    """Tail the Ollama server log in real time.

    Shows the last N lines then streams new entries as they arrive.
    Useful for watching phi4-mini's raw token generation and server errors.

    Example:
        mcli run trading_research logs
        mcli run trading_research logs -n 100
    """
    log_path = Path("/opt/homebrew/var/log/ollama.log")
    if not log_path.exists():
        # Fallback: check common alternative locations
        fallbacks = [
            Path.home() / ".ollama" / "logs" / "server.log",
            Path("/usr/local/var/log/ollama.log"),
        ]
        for fb in fallbacks:
            if fb.exists():
                log_path = fb
                break
        else:
            click.echo(f"[error] Ollama log not found. Checked:\n  {log_path}")
            for fb in fallbacks:
                click.echo(f"  {fb}")
            click.echo("\nTry: brew services info ollama  (to find log location)")
            raise SystemExit(1)

    click.echo(f"Tailing Ollama log: {log_path}")
    click.echo("(Ctrl+C to stop)\n")

    try:
        with subprocess.Popen(
            ["tail", f"-{lines}", "-f", str(log_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        ) as proc:
            try:
                for line in proc.stdout:
                    print(line, end="", flush=True)
            except KeyboardInterrupt:
                proc.terminate()
                proc.wait()
    except KeyboardInterrupt:
        pass
