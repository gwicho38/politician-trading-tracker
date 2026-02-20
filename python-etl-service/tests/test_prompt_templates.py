"""Tests for LLM prompt templates."""

import re
from pathlib import Path

import pytest

from app.prompts import load_template, render_template, PROMPTS_DIR


TEMPLATE_NAMES = [
    "validation_gate",
    "anomaly_detection",
    "lineage_audit",
    "feedback_loop",
]


class TestTemplateFilesExist:
    """Verify that all template files exist and are non-empty."""

    @pytest.mark.parametrize("name", TEMPLATE_NAMES)
    def test_template_file_exists(self, name: str):
        path = PROMPTS_DIR / f"{name}.txt"
        assert path.exists(), f"Template file {name}.txt does not exist"

    @pytest.mark.parametrize("name", TEMPLATE_NAMES)
    def test_template_file_non_empty(self, name: str):
        path = PROMPTS_DIR / f"{name}.txt"
        content = path.read_text()
        assert len(content.strip()) > 0, f"Template file {name}.txt is empty"


class TestLoadTemplate:
    """Test load_template function."""

    @pytest.mark.parametrize("name", TEMPLATE_NAMES)
    def test_load_template_returns_string(self, name: str):
        result = load_template(name)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_load_template_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            load_template("nonexistent_template")

    def test_validation_gate_contains_batch_json_placeholder(self):
        content = load_template("validation_gate")
        assert "{{ batch_json }}" in content

    def test_anomaly_detection_contains_placeholders(self):
        content = load_template("anomaly_detection")
        assert "{{ start_date }}" in content
        assert "{{ end_date }}" in content
        assert "{{ filer_names_or_ALL }}" in content
        assert "{{ calendar_events_json }}" in content
        assert "{{ trading_records_json }}" in content
        assert "{{ baseline_stats_json }}" in content

    def test_lineage_audit_contains_placeholders(self):
        content = load_template("lineage_audit")
        assert "{{ record_json }}" in content
        assert "{{ source_url }}" in content
        assert "{{ source_hash }}" in content
        assert "{{ method }}" in content
        assert "{{ extraction_ts }}" in content
        assert "{{ transform_chain_json }}" in content
        assert "{{ current_hash }}" in content

    def test_feedback_loop_contains_placeholders(self):
        content = load_template("feedback_loop")
        assert "{{ start_date }}" in content
        assert "{{ end_date }}" in content
        assert "{{ signals_with_outcomes_json }}" in content
        assert "{{ validation_version }}" in content
        assert "{{ anomaly_version }}" in content
        assert "{{ thresholds_json }}" in content


class TestRenderTemplate:
    """Test render_template function with variable substitution."""

    def test_render_validation_gate(self):
        result = render_template("validation_gate", batch_json='[{"ticker": "AAPL"}]')
        assert '[{"ticker": "AAPL"}]' in result
        assert "{{ batch_json }}" not in result

    def test_render_anomaly_detection_all_vars(self):
        result = render_template(
            "anomaly_detection",
            start_date="2026-01-01",
            end_date="2026-01-31",
            filer_names_or_ALL="ALL",
            calendar_events_json="[]",
            trading_records_json="[]",
            baseline_stats_json="{}",
        )
        assert "{{ start_date }}" not in result
        assert "{{ end_date }}" not in result
        assert "{{ filer_names_or_ALL }}" not in result
        assert "{{ calendar_events_json }}" not in result
        assert "{{ trading_records_json }}" not in result
        assert "{{ baseline_stats_json }}" not in result
        assert "2026-01-01" in result
        assert "2026-01-31" in result

    def test_render_lineage_audit_all_vars(self):
        result = render_template(
            "lineage_audit",
            record_json='{"id": "rec-1"}',
            source_url="https://efdsearch.senate.gov/filing/123",
            source_hash="abc123",
            method="html_scrape",
            extraction_ts="2026-01-15T10:00:00Z",
            transform_chain_json="[]",
            current_hash="def456",
        )
        assert "{{ record_json }}" not in result
        assert "{{ source_url }}" not in result
        assert "{{ source_hash }}" not in result
        assert "{{ method }}" not in result
        assert "{{ extraction_ts }}" not in result
        assert "{{ transform_chain_json }}" not in result
        assert "{{ current_hash }}" not in result
        assert "abc123" in result
        assert "def456" in result

    def test_render_feedback_loop_all_vars(self):
        result = render_template(
            "feedback_loop",
            start_date="2026-01-01",
            end_date="2026-01-31",
            signals_with_outcomes_json="[]",
            validation_version="1.0.0",
            anomaly_version="1.0.0",
            thresholds_json="{}",
        )
        assert "{{ start_date }}" not in result
        assert "{{ end_date }}" not in result
        assert "{{ signals_with_outcomes_json }}" not in result
        assert "{{ validation_version }}" not in result
        assert "{{ anomaly_version }}" not in result
        assert "{{ thresholds_json }}" not in result

    def test_render_no_remaining_placeholders_validation_gate(self):
        """When all variables are provided, no {{ }} placeholders should remain."""
        result = render_template("validation_gate", batch_json="[]")
        remaining = re.findall(r"\{\{.*?\}\}", result)
        assert len(remaining) == 0, f"Remaining placeholders: {remaining}"

    def test_render_no_remaining_placeholders_anomaly_detection(self):
        result = render_template(
            "anomaly_detection",
            start_date="2026-01-01",
            end_date="2026-01-31",
            filer_names_or_ALL="ALL",
            calendar_events_json="[]",
            trading_records_json="[]",
            baseline_stats_json="{}",
        )
        remaining = re.findall(r"\{\{.*?\}\}", result)
        assert len(remaining) == 0, f"Remaining placeholders: {remaining}"

    def test_render_no_remaining_placeholders_lineage_audit(self):
        result = render_template(
            "lineage_audit",
            record_json="{}",
            source_url="https://example.com",
            source_hash="abc",
            method="api",
            extraction_ts="2026-01-15T10:00:00Z",
            transform_chain_json="[]",
            current_hash="def",
        )
        remaining = re.findall(r"\{\{.*?\}\}", result)
        assert len(remaining) == 0, f"Remaining placeholders: {remaining}"

    def test_render_no_remaining_placeholders_feedback_loop(self):
        result = render_template(
            "feedback_loop",
            start_date="2026-01-01",
            end_date="2026-01-31",
            signals_with_outcomes_json="[]",
            validation_version="1.0.0",
            anomaly_version="1.0.0",
            thresholds_json="{}",
        )
        remaining = re.findall(r"\{\{.*?\}\}", result)
        assert len(remaining) == 0, f"Remaining placeholders: {remaining}"

    def test_render_partial_substitution_leaves_other_placeholders(self):
        """If not all variables are provided, remaining placeholders stay."""
        result = render_template("anomaly_detection", start_date="2026-01-01")
        assert "2026-01-01" in result
        assert "{{ end_date }}" in result


class TestVersionHeaders:
    """Test that all templates have proper version headers."""

    @pytest.mark.parametrize("name", TEMPLATE_NAMES)
    def test_template_has_version_header(self, name: str):
        content = load_template(name)
        assert "# Version:" in content, f"Template {name} missing version header"

    @pytest.mark.parametrize("name", TEMPLATE_NAMES)
    def test_version_header_is_parseable(self, name: str):
        content = load_template(name)
        match = re.search(r"# Version:\s*(\d+\.\d+\.\d+)", content)
        assert match is not None, f"Template {name} has unparseable version header"
        version = match.group(1)
        parts = version.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()

    @pytest.mark.parametrize("name", TEMPLATE_NAMES)
    def test_template_has_service_header(self, name: str):
        content = load_template(name)
        assert "# Service:" in content, f"Template {name} missing service header"

    @pytest.mark.parametrize("name", TEMPLATE_NAMES)
    def test_service_header_is_parseable(self, name: str):
        content = load_template(name)
        match = re.search(r"# Service:\s*(\S+)", content)
        assert match is not None, f"Template {name} has unparseable service header"
        service_name = match.group(1)
        assert len(service_name) > 0


class TestTemplateContent:
    """Test that templates contain expected structural elements."""

    @pytest.mark.parametrize("name", TEMPLATE_NAMES)
    def test_template_has_system_section(self, name: str):
        content = load_template(name)
        assert "SYSTEM:" in content, f"Template {name} missing SYSTEM section"

    @pytest.mark.parametrize("name", TEMPLATE_NAMES)
    def test_template_has_user_section(self, name: str):
        content = load_template(name)
        assert "USER:" in content, f"Template {name} missing USER section"

    def test_validation_gate_mentions_stock_act(self):
        content = load_template("validation_gate")
        assert "STOCK Act" in content

    def test_anomaly_detection_mentions_phases(self):
        content = load_template("anomaly_detection")
        assert "PHASE 1" in content
        assert "PHASE 2" in content
        assert "PHASE 3" in content
        assert "PHASE 4" in content

    def test_lineage_audit_mentions_chain_of_verification(self):
        content = load_template("lineage_audit")
        assert "Chain-of-Verification" in content or "Verification" in content

    def test_feedback_loop_mentions_signal_quality(self):
        content = load_template("feedback_loop")
        assert "Signal Quality" in content or "signal quality" in content or "Signal" in content
