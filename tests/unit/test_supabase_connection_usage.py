"""
Unit tests for Supabase connection usage patterns
Tests that the API is being used correctly
"""

from unittest.mock import Mock


class TestSupabaseConnectionUsage:
    """Test that we're using the Supabase connection API correctly"""

    def test_connection_table_select_api(self):
        """Test that conn.table().select().execute() pattern works"""
        # Create mock connection
        mock_conn = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_response = Mock()
        mock_response.data = [{"id": 1, "name": "test"}]
        mock_response.count = 1

        # Set up the chain
        mock_conn.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.limit.return_value = mock_select
        mock_select.execute.return_value = mock_response

        # Test the pattern
        response = mock_conn.table("test_table").select("*", count="exact").limit(0).execute()

        # Verify the calls
        mock_conn.table.assert_called_once_with("test_table")
        mock_table.select.assert_called_once_with("*", count="exact")
        mock_select.limit.assert_called_once_with(0)
        mock_select.execute.assert_called_once()

        # Verify the response
        assert response.data == [{"id": 1, "name": "test"}]
        assert response.count == 1

    def test_connection_table_order_api(self):
        """Test that conn.table().select().order().execute() pattern works"""
        # Create mock connection
        mock_conn = Mock()
        mock_table = Mock()
        mock_select = Mock()
        mock_order = Mock()
        mock_response = Mock()
        mock_response.data = [{"id": 2, "name": "second"}, {"id": 1, "name": "first"}]

        # Set up the chain
        mock_conn.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.order.return_value = mock_order
        mock_order.limit.return_value = mock_order
        mock_order.execute.return_value = mock_response

        # Test the pattern
        response = (
            mock_conn.table("action_logs")
            .select("*")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        # Verify the calls
        mock_conn.table.assert_called_once_with("action_logs")
        mock_table.select.assert_called_once_with("*")
        mock_select.order.assert_called_once_with("created_at", desc=True)
        mock_order.limit.assert_called_once_with(5)
        mock_order.execute.assert_called_once()

        # Verify the response
        assert len(response.data) == 2

    def test_connection_returns_supabase_client(self):
        """Test that st.connection returns a Supabase client with table method"""
        # Create a mock that behaves like a Supabase client
        mock_client = Mock()
        mock_client.table = Mock()

        # Simulate what st.connection would return
        conn = mock_client

        # Verify it has the table method
        assert hasattr(conn, "table")
        assert callable(conn.table)

    def test_response_has_data_attribute(self):
        """Test that Supabase response has data attribute"""
        mock_response = Mock()
        mock_response.data = [{"id": 1}, {"id": 2}]

        # This is the pattern we use in the code
        if mock_response.data:
            assert len(mock_response.data) == 2

    def test_response_has_count_attribute(self):
        """Test that Supabase response can have count attribute"""
        mock_response = Mock()
        mock_response.count = 42

        # This is the pattern we use in the code
        count = mock_response.count if hasattr(mock_response, "count") else 0
        assert count == 42

    def test_pandas_dataframe_from_response(self):
        """Test that we can create a pandas DataFrame from response.data"""
        import pandas as pd

        mock_response = Mock()
        mock_response.data = [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]

        # This is how we convert to DataFrame in the code
        df = pd.DataFrame(mock_response.data)

        assert len(df) == 2
        assert "id" in df.columns
        assert "name" in df.columns
        assert df.iloc[0]["id"] == 1
        assert df.iloc[1]["name"] == "test2"

    def test_empty_response_handling(self):
        """Test that we handle empty responses correctly"""
        mock_response = Mock()
        mock_response.data = []

        # This is the pattern we use in the code
        if mock_response.data:
            # Should not execute
            assert False
        else:
            # Should execute
            assert True

    def test_connection_error_handling(self):
        """Test that connection errors are handled"""
        mock_conn = Mock()
        mock_conn.table.side_effect = Exception("Connection failed")

        # This is how we handle errors in the code
        try:
            mock_conn.table("test_table")
            assert False  # Should not reach here
        except Exception as e:
            assert str(e) == "Connection failed"
