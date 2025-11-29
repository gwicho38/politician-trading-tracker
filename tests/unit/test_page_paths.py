"""
Unit tests for validating Streamlit page paths.

This test ensures that all st.switch_page() calls reference valid page files
that exist in the correct location (src/ directory).
"""

import os
import re


# Project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Expected page files in src/ directory
EXPECTED_PAGES = [
    "src/1_📥_Data_Collection.py",
    "src/2_🎯_Trading_Signals.py",
    "src/3_💼_Trading_Operations.py",
    "src/4_📈_Portfolio.py",
    "src/4.5_📋_Orders.py",
    "src/5_⏰_Scheduled_Jobs.py",
    "src/6_⚙️_Settings.py",
    "src/7_🔧_Database_Setup.py",
    "src/8_📋_Action_Logs.py",
    "src/9_🛒_Cart.py",
    "src/10_💳_Subscription.py",
    "src/11_🔐_Admin.py",
    "src/99_🧪_Auth_Test.py",
]


class TestPagePaths:
    """Test cases for page path validation."""

    def test_expected_pages_exist(self):
        """Verify all expected page files exist."""
        for page_path in EXPECTED_PAGES:
            full_path = os.path.join(PROJECT_ROOT, page_path)
            assert os.path.exists(full_path), f"Expected page file does not exist: {page_path}"

    def test_switch_page_paths_in_shopping_cart(self):
        """Verify st.switch_page() calls in shopping_cart.py use correct paths."""
        file_path = os.path.join(PROJECT_ROOT, "src", "shopping_cart.py")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find all st.switch_page() calls
        switch_page_pattern = r'st\.switch_page\(["\']([^"\']+)["\']\)'
        matches = re.findall(switch_page_pattern, content)

        assert len(matches) > 0, "No st.switch_page() calls found in shopping_cart.py"

        for page_path in matches:
            assert page_path.startswith("src/"), (
                f"Invalid page path in shopping_cart.py: {page_path}. "
                f"Should start with 'src/'"
            )
            full_path = os.path.join(PROJECT_ROOT, page_path)
            assert os.path.exists(full_path), (
                f"Page file referenced in shopping_cart.py does not exist: {page_path}"
            )

    def test_switch_page_paths_in_hotkeys_integration(self):
        """Verify st.switch_page() calls in streamlit_hotkeys_integration.py use correct paths."""
        file_path = os.path.join(PROJECT_ROOT, "src", "streamlit_hotkeys_integration.py")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find all st.switch_page() calls
        switch_page_pattern = r'st\.switch_page\(["\']([^"\']+)["\']\)'
        matches = re.findall(switch_page_pattern, content)

        assert len(matches) > 0, "No st.switch_page() calls found in streamlit_hotkeys_integration.py"

        for page_path in matches:
            assert page_path.startswith("src/"), (
                f"Invalid page path in streamlit_hotkeys_integration.py: {page_path}. "
                f"Should start with 'src/'"
            )
            full_path = os.path.join(PROJECT_ROOT, page_path)
            assert os.path.exists(full_path), (
                f"Page file referenced in streamlit_hotkeys_integration.py does not exist: {page_path}"
            )

    def test_switch_page_paths_in_command_palette(self):
        """Verify st.switch_page() calls in command_palette.py use correct paths."""
        file_path = os.path.join(PROJECT_ROOT, "src", "command_palette.py")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Find all st.switch_page() calls
        switch_page_pattern = r'st\.switch_page\(["\']([^"\']+)["\']\)'
        matches = re.findall(switch_page_pattern, content)

        assert len(matches) > 0, "No st.switch_page() calls found in command_palette.py"

        for page_path in matches:
            assert page_path.startswith("src/"), (
                f"Invalid page path in command_palette.py: {page_path}. "
                f"Should start with 'src/'"
            )
            full_path = os.path.join(PROJECT_ROOT, page_path)
            assert os.path.exists(full_path), (
                f"Page file referenced in command_palette.py does not exist: {page_path}"
            )

    def test_no_invalid_page_paths_in_codebase(self):
        """Scan entire src/ directory for any st.switch_page() calls with invalid paths."""
        src_dir = os.path.join(PROJECT_ROOT, "src")
        switch_page_pattern = r'st\.switch_page\(["\']([^"\']+)["\']\)'

        invalid_paths = []

        for filename in os.listdir(src_dir):
            if filename.endswith(".py"):
                file_path = os.path.join(src_dir, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                matches = re.findall(switch_page_pattern, content)
                for page_path in matches:
                    # Check if path starts with src/ and file exists
                    if not page_path.startswith("src/"):
                        invalid_paths.append((filename, page_path, "Missing 'src/' prefix"))
                    else:
                        full_path = os.path.join(PROJECT_ROOT, page_path)
                        if not os.path.exists(full_path):
                            invalid_paths.append((filename, page_path, "File does not exist"))

        assert len(invalid_paths) == 0, (
            "Found invalid st.switch_page() paths:\n" +
            "\n".join([f"  {f}: {p} ({r})" for f, p, r in invalid_paths])
        )
