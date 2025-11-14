"""
Unit tests for analytics data parsing logic
Tests the logic used in the Admin dashboard to parse analytics.json
"""


class TestAnalyticsParsing:
    """Test analytics data parsing logic"""

    def test_parse_simple_widgets(self):
        """Test parsing widgets with simple integer values"""
        widgets = {"Button A": 5, "Button B": 10, "Button C": 3}

        total_interactions = 0
        for widget_name, widget_value in widgets.items():
            if isinstance(widget_value, int):
                total_interactions += widget_value
            elif isinstance(widget_value, dict):
                total_interactions += sum(v for v in widget_value.values() if isinstance(v, int))

        assert total_interactions == 18

    def test_parse_nested_widgets(self):
        """Test parsing widgets with nested dictionary values"""
        widgets = {
            "Select log file": {
                "logs/2025-11-01.log": 2,
                "logs/2025-11-02.log": 1,
                "logs/2025-11-03.log": 0,
            }
        }

        total_interactions = 0
        for widget_name, widget_value in widgets.items():
            if isinstance(widget_value, int):
                total_interactions += widget_value
            elif isinstance(widget_value, dict):
                total_interactions += sum(v for v in widget_value.values() if isinstance(v, int))

        assert total_interactions == 3

    def test_parse_mixed_widgets(self):
        """Test parsing widgets with both simple and nested values"""
        widgets = {
            "Button A": 5,
            "Select dropdown": {"Option 1": 2, "Option 2": 3, "Option 3": 1},
            "Button B": 10,
            "Radio group": {"Choice A": 4, "Choice B": 0},
        }

        total_interactions = 0
        for widget_name, widget_value in widgets.items():
            if isinstance(widget_value, int):
                total_interactions += widget_value
            elif isinstance(widget_value, dict):
                total_interactions += sum(v for v in widget_value.values() if isinstance(v, int))

        # 5 (Button A) + (2+3+1) (Select) + 10 (Button B) + (4+0) (Radio) = 25
        assert total_interactions == 25

    def test_parse_real_analytics_data(self):
        """Test parsing actual analytics data structure from analytics.json"""
        analytics_data = {
            "loaded_from_firestore": False,
            "total_pageviews": 1,
            "total_script_runs": 1,
            "widgets": {
                "Refresh interval": {
                    "Real-time (2s)": 0,
                    "Fast (5s)": 0,
                    "Medium (10s)": 1,
                    "Slow (30s)": 0,
                    "Very slow (1m)": 0,
                },
                "🚀 Start Tracking": 0,
                "🛑 Stop Tracking": 0,
                "Select log file": {
                    "logs/2025-11-01.log": 1,
                    "logs/latest.log": 0,
                    "logs/2025-11-03.log": 0,
                    "logs/2025-11-02.log": 0,
                    "logs/2025-11-04.log": 0,
                },
                "Lines to show": {"100": 1},
            },
        }

        # Calculate total interactions
        total_interactions = 0
        widgets = analytics_data.get("widgets", {})
        for widget_name, widget_value in widgets.items():
            if isinstance(widget_value, int):
                total_interactions += widget_value
            elif isinstance(widget_value, dict):
                total_interactions += sum(v for v in widget_value.values() if isinstance(v, int))

        # Refresh: 1, Start: 0, Stop: 0, Select: 1, Lines: 1 = 3
        assert total_interactions == 3

        # Check other metrics
        assert analytics_data.get("total_pageviews", 0) == 1
        assert analytics_data.get("total_script_runs", 0) == 1
        assert len(analytics_data.get("widgets", {})) == 5

    def test_parse_empty_widgets(self):
        """Test parsing when widgets is empty"""
        widgets = {}

        total_interactions = 0
        for widget_name, widget_value in widgets.items():
            if isinstance(widget_value, int):
                total_interactions += widget_value
            elif isinstance(widget_value, dict):
                total_interactions += sum(v for v in widget_value.values() if isinstance(v, int))

        assert total_interactions == 0

    def test_parse_widgets_with_string_values(self):
        """Test that string values are ignored (shouldn't happen, but be safe)"""
        widgets = {
            "Button A": 5,
            "Invalid": "not a number",
            "Select": {"Option 1": 2, "Invalid Option": "also not a number", "Option 2": 3},
        }

        total_interactions = 0
        for widget_name, widget_value in widgets.items():
            if isinstance(widget_value, int):
                total_interactions += widget_value
            elif isinstance(widget_value, dict):
                total_interactions += sum(v for v in widget_value.values() if isinstance(v, int))

        # Should only count integers: 5 + 2 + 3 = 10
        assert total_interactions == 10

    def test_unique_widgets_count(self):
        """Test counting unique widgets"""
        widgets = {
            "Button A": 5,
            "Select dropdown": {"Option 1": 2, "Option 2": 3},
            "Button B": 10,
            "Radio group": {"Choice A": 4},
        }

        unique_widgets = len(widgets)
        assert unique_widgets == 4

    def test_handle_missing_fields(self):
        """Test handling when expected fields are missing"""
        analytics_data = {
            "loaded_from_firestore": False
            # Missing total_pageviews, total_script_runs, widgets
        }

        # Should not raise errors
        total_views = analytics_data.get("total_pageviews", 0)
        total_runs = analytics_data.get("total_script_runs", 0)
        widgets = analytics_data.get("widgets", {})

        assert total_views == 0
        assert total_runs == 0
        assert len(widgets) == 0
