"""LLM prompt templates for the ETL pipeline.

Provides helpers to load and render prompt templates with variable substitution.
Templates use {{ variable_name }} placeholders (double curly braces with spaces).
"""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


def load_template(name: str) -> str:
    """Load a prompt template by name (without .txt extension).

    Args:
        name: Template name, e.g. "validation_gate"

    Returns:
        Raw template content as a string.

    Raises:
        FileNotFoundError: If the template file does not exist.
    """
    path = PROMPTS_DIR / f"{name}.txt"
    return path.read_text()


def render_template(name: str, **kwargs: str) -> str:
    """Load and render a prompt template with variable substitution.

    Replaces {{ key }} placeholders with provided values.
    Any placeholders not provided in kwargs are left as-is.

    Args:
        name: Template name, e.g. "validation_gate"
        **kwargs: Variable name/value pairs to substitute.

    Returns:
        Rendered template string.
    """
    template = load_template(name)
    for key, value in kwargs.items():
        template = template.replace(f"{{{{ {key} }}}}", str(value))
    return template
