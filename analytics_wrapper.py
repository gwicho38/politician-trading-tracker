"""
Analytics wrapper to handle PosixPath serialization issues
"""
import json
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Dict

try:
    import streamlit_analytics
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False


def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively sanitize objects to be JSON-serializable.
    Converts PosixPath objects to strings.
    """
    if isinstance(obj, Path):
        return str(obj)
    elif isinstance(obj, dict):
        return {sanitize_for_json(k): sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        # Convert other objects to strings
        return str(obj)


@contextmanager
def safe_track(save_to_json: str = None, load_from_json: str = None, **kwargs):
    """
    Wrapper around streamlit_analytics.track that sanitizes data before saving.
    """
    if not ANALYTICS_AVAILABLE:
        yield
        return

    # Start tracking
    streamlit_analytics.start_tracking(**kwargs)

    try:
        yield
    finally:
        # Stop tracking and get counts
        counts = streamlit_analytics.counts

        # Sanitize the data
        sanitized_counts = sanitize_for_json(counts)

        # Save to JSON if specified
        if save_to_json:
            with open(save_to_json, 'w') as f:
                json.dump(sanitized_counts, f, indent=2)

        # Stop tracking without saving (we already saved)
        streamlit_analytics.stop_tracking(
            unsafe_password=kwargs.get('unsafe_password'),
            firestore_key_file=kwargs.get('firestore_key_file'),
            firestore_collection_name=kwargs.get('firestore_collection_name'),
            save_to_json=None,  # Don't save again
            verbose=kwargs.get('verbose', False)
        )
