"""
Unit tests for analytics_wrapper module
"""

import json
import sys
import tempfile
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from analytics_wrapper import sanitize_for_json


class TestSanitizeForJson:
    """Test the sanitize_for_json function"""

    def test_sanitize_posix_path(self):
        """Test that PosixPath objects are converted to strings"""
        path = Path("/tmp/test.txt")
        result = sanitize_for_json(path)
        assert isinstance(result, str)
        assert result == "/tmp/test.txt"

    def test_sanitize_dict_with_posix_path_keys(self):
        """Test that dictionaries with PosixPath keys are sanitized"""
        path = Path("/tmp/test.txt")
        data = {path: "value"}
        result = sanitize_for_json(data)
        assert isinstance(result, dict)
        assert "/tmp/test.txt" in result
        assert result["/tmp/test.txt"] == "value"

    def test_sanitize_dict_with_posix_path_values(self):
        """Test that dictionaries with PosixPath values are sanitized"""
        path = Path("/tmp/test.txt")
        data = {"key": path}
        result = sanitize_for_json(data)
        assert isinstance(result, dict)
        assert result["key"] == "/tmp/test.txt"

    def test_sanitize_nested_dict(self):
        """Test that nested dictionaries are sanitized"""
        path1 = Path("/tmp/test1.txt")
        path2 = Path("/tmp/test2.txt")
        data = {"outer": {path1: "value1", "inner": {"key": path2}}}
        result = sanitize_for_json(data)
        assert isinstance(result, dict)
        assert "/tmp/test1.txt" in result["outer"]
        assert result["outer"]["inner"]["key"] == "/tmp/test2.txt"

    def test_sanitize_list(self):
        """Test that lists with PosixPath objects are sanitized"""
        path1 = Path("/tmp/test1.txt")
        path2 = Path("/tmp/test2.txt")
        data = [path1, "string", path2]
        result = sanitize_for_json(data)
        assert isinstance(result, list)
        assert result == ["/tmp/test1.txt", "string", "/tmp/test2.txt"]

    def test_sanitize_preserves_primitives(self):
        """Test that primitive types are preserved"""
        data = {"string": "value", "int": 42, "float": 3.14, "bool": True, "none": None}
        result = sanitize_for_json(data)
        assert result == data

    def test_sanitized_data_is_json_serializable(self):
        """Test that sanitized data can be serialized to JSON"""
        path1 = Path("/tmp/test1.txt")
        path2 = Path("/tmp/test2.txt")
        data = {"paths": [path1, path2], "nested": {path1: "value", "key": path2}}
        result = sanitize_for_json(data)

        # Should not raise an exception
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            json.dump(result, f)
            temp_path = f.name

        # Verify it can be loaded back
        with open(temp_path, "r") as f:
            loaded = json.load(f)

        assert "/tmp/test1.txt" in loaded["nested"]
        assert loaded["paths"] == ["/tmp/test1.txt", "/tmp/test2.txt"]

        # Cleanup
        Path(temp_path).unlink()

    def test_sanitize_tuple(self):
        """Test that tuples are converted to lists"""
        path = Path("/tmp/test.txt")
        data = (path, "string", 42)
        result = sanitize_for_json(data)
        assert isinstance(result, list)
        assert result == ["/tmp/test.txt", "string", 42]

    def test_sanitize_complex_object(self):
        """Test that complex non-serializable objects are converted to strings"""

        class CustomObject:
            def __str__(self):
                return "custom_object"

        obj = CustomObject()
        result = sanitize_for_json(obj)
        assert isinstance(result, str)
        assert result == "custom_object"
