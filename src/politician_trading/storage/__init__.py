"""
Storage package for managing raw data files.

Provides StorageManager for saving/retrieving PDFs, API responses,
and parsed data from Supabase Storage.
"""

from .storage_manager import StorageManager

__all__ = ['StorageManager']
