"""
Storage Manager for Supabase Storage.

Handles saving and retrieving raw data files (PDFs, API responses, etc.)
with proper metadata tracking.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class StorageManager:
    """
    Manage file storage in Supabase Storage buckets.

    Handles:
    - Saving PDFs from Senate/House
    - Saving API responses (QuiverQuant, etc.)
    - Saving parsed intermediate data
    - Metadata tracking in database
    - File retrieval for reprocessing
    """

    def __init__(self, supabase_client):
        """
        Initialize storage manager.

        Args:
            supabase_client: Supabase client instance
        """
        self.client = supabase_client
        self.logger = logging.getLogger(__name__)

    async def save_pdf(
        self,
        pdf_content: bytes,
        disclosure_id: str,
        politician_name: str,
        source_url: str,
        transaction_date: datetime,
        source_type: str = "senate_pdf"
    ) -> tuple[str, str]:
        """
        Save PDF to storage and create database record.

        Args:
            pdf_content: PDF file bytes
            disclosure_id: Disclosure UUID
            politician_name: Politician name for filename
            source_url: Original URL where PDF was downloaded from
            transaction_date: Date of transaction (for folder structure)
            source_type: Type of source (senate_pdf, house_pdf, etc.)

        Returns:
            Tuple of (storage_path, file_id)
        """
        try:
            # Generate path
            year = transaction_date.year
            month = f"{transaction_date.month:02d}"
            date_str = transaction_date.strftime("%Y%m%d")

            # Clean politician name for filename
            clean_name = "".join(c for c in politician_name if c.isalnum() or c in (' ', '-'))
            clean_name = clean_name.replace(' ', '_')[:50]

            filename = f"{disclosure_id}_{clean_name}_{date_str}.pdf"

            # Determine chamber from source_type
            chamber = "senate" if "senate" in source_type.lower() else "house"
            path = f"{chamber}/{year}/{month}/{filename}"

            self.logger.info(f"Saving PDF to storage: {path}")

            # Calculate hash
            file_hash = hashlib.sha256(pdf_content).hexdigest()

            # Upload to storage
            self.client.storage.from_('raw-pdfs').upload(
                path,
                pdf_content,
                {
                    'content-type': 'application/pdf',
                    'x-upsert': 'true'  # Overwrite if exists
                }
            )

            self.logger.debug(f"PDF uploaded successfully: {len(pdf_content)} bytes")

            # Save metadata to database
            metadata = {
                'disclosure_id': disclosure_id,
                'storage_bucket': 'raw-pdfs',
                'storage_path': path,
                'file_type': 'pdf',
                'file_size_bytes': len(pdf_content),
                'file_hash_sha256': file_hash,
                'mime_type': 'application/pdf',
                'source_url': source_url,
                'source_type': source_type,
                'parse_status': 'pending',
                'expires_at': (datetime.utcnow() + timedelta(days=365)).isoformat()  # 1 year retention
            }

            response = self.client.table('stored_files').insert(metadata).execute()

            file_id = response.data[0]['id'] if response.data else None

            self.logger.info(f"PDF metadata saved: file_id={file_id}")

            # Update disclosure record
            if file_id:
                self.client.table('trading_disclosures').update({
                    'source_file_id': file_id,
                    'has_raw_pdf': True
                }).eq('id', disclosure_id).execute()

            return path, file_id

        except Exception as e:
            self.logger.error(f"Error saving PDF: {e}", exc_info=True)
            raise

    async def save_api_response(
        self,
        response_data: Dict[str, Any],
        source: str,
        endpoint: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[str, str]:
        """
        Save API response JSON to storage.

        Args:
            response_data: API response data (dict)
            source: Source name (quiverquant, house_api, etc.)
            endpoint: API endpoint called
            metadata: Additional metadata

        Returns:
            Tuple of (storage_path, file_id)
        """
        try:
            # Generate path with timestamp
            now = datetime.utcnow()
            date_path = now.strftime("%Y/%m/%d")
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            filename = f"batch_{timestamp}.json"
            path = f"{source}/{date_path}/{filename}"

            self.logger.info(f"Saving API response to storage: {path}")

            # Convert to JSON
            json_content = json.dumps(response_data, indent=2)
            json_bytes = json_content.encode('utf-8')

            # Calculate hash
            file_hash = hashlib.sha256(json_bytes).hexdigest()

            # Upload
            self.client.storage.from_('api-responses').upload(
                path,
                json_bytes,
                {
                    'content-type': 'application/json',
                    'x-upsert': 'true'
                }
            )

            self.logger.debug(f"API response uploaded: {len(json_bytes)} bytes")

            # Count records in response
            record_count = 0
            if isinstance(response_data, list):
                record_count = len(response_data)
            elif isinstance(response_data, dict):
                # Try common keys for record lists
                for key in ['data', 'trades', 'results', 'records']:
                    if key in response_data and isinstance(response_data[key], list):
                        record_count = len(response_data[key])
                        break

            # Save metadata to database
            db_metadata = {
                'storage_bucket': 'api-responses',
                'storage_path': path,
                'file_type': 'json',
                'file_size_bytes': len(json_bytes),
                'file_hash_sha256': file_hash,
                'mime_type': 'application/json',
                'source_type': f'{source}_api',
                'parse_status': 'pending',
                'transactions_found': record_count,
                'expires_at': (datetime.utcnow() + timedelta(days=90)).isoformat()  # 90 day retention
            }

            # Add custom metadata if provided
            if metadata:
                db_metadata['source_url'] = metadata.get('url', '')

            response = self.client.table('stored_files').insert(db_metadata).execute()

            file_id = response.data[0]['id'] if response.data else None

            self.logger.info(f"API response metadata saved: file_id={file_id}, records={record_count}")

            return path, file_id

        except Exception as e:
            self.logger.error(f"Error saving API response: {e}", exc_info=True)
            raise

    async def save_parsed_data(
        self,
        parsed_data: Dict[str, Any],
        source_file_id: str,
        disclosure_id: Optional[str] = None
    ) -> tuple[str, str]:
        """
        Save parsed/intermediate data.

        Args:
            parsed_data: Parsed data dictionary
            source_file_id: ID of source file (PDF or API response)
            disclosure_id: Optional disclosure ID

        Returns:
            Tuple of (storage_path, file_id)
        """
        try:
            # Generate path
            now = datetime.utcnow()
            date_path = now.strftime("%Y/%m/%d")
            timestamp = now.strftime("%Y%m%d_%H%M%S")

            if disclosure_id:
                filename = f"{disclosure_id}_parsed_{timestamp}.json"
            else:
                filename = f"batch_parsed_{timestamp}.json"

            path = f"parsed/{date_path}/{filename}"

            self.logger.info(f"Saving parsed data to storage: {path}")

            # Convert to JSON
            json_content = json.dumps(parsed_data, indent=2, default=str)
            json_bytes = json_content.encode('utf-8')

            # Upload
            self.client.storage.from_('parsed-data').upload(
                path,
                json_bytes,
                {
                    'content-type': 'application/json',
                    'x-upsert': 'true'
                }
            )

            # Save metadata
            metadata = {
                'disclosure_id': disclosure_id,
                'storage_bucket': 'parsed-data',
                'storage_path': path,
                'file_type': 'json',
                'file_size_bytes': len(json_bytes),
                'mime_type': 'application/json',
                'source_type': 'parsed_data',
                'parse_status': 'success',
                'expires_at': (datetime.utcnow() + timedelta(days=730)).isoformat()  # 2 year retention
            }

            response = self.client.table('stored_files').insert(metadata).execute()

            file_id = response.data[0]['id'] if response.data else None

            # Update disclosure record
            if disclosure_id:
                self.client.table('trading_disclosures').update({
                    'has_parsed_data': True
                }).eq('id', disclosure_id).execute()

            return path, file_id

        except Exception as e:
            self.logger.error(f"Error saving parsed data: {e}", exc_info=True)
            raise

    async def get_pdf(self, storage_path: str) -> bytes:
        """
        Retrieve PDF from storage.

        Args:
            storage_path: Path within raw-pdfs bucket

        Returns:
            PDF content as bytes
        """
        try:
            self.logger.debug(f"Retrieving PDF: {storage_path}")
            response = self.client.storage.from_('raw-pdfs').download(storage_path)
            return response
        except Exception as e:
            self.logger.error(f"Error retrieving PDF: {e}", exc_info=True)
            raise

    async def get_api_response(self, storage_path: str) -> Dict[str, Any]:
        """
        Retrieve API response from storage.

        Args:
            storage_path: Path within api-responses bucket

        Returns:
            API response as dictionary
        """
        try:
            self.logger.debug(f"Retrieving API response: {storage_path}")
            response = self.client.storage.from_('api-responses').download(storage_path)
            return json.loads(response)
        except Exception as e:
            self.logger.error(f"Error retrieving API response: {e}", exc_info=True)
            raise

    async def mark_file_parsed(
        self,
        file_id: str,
        transactions_count: int = 0
    ):
        """Mark file as successfully parsed"""
        try:
            self.client.rpc('mark_file_parsed', {
                'p_file_id': file_id,
                'p_transactions_count': transactions_count
            }).execute()
            self.logger.info(f"File marked as parsed: {file_id}")
        except Exception as e:
            self.logger.error(f"Error marking file as parsed: {e}")

    async def mark_file_failed(
        self,
        file_id: str,
        error_message: str
    ):
        """Mark file as failed to parse"""
        try:
            self.client.rpc('mark_file_failed', {
                'p_file_id': file_id,
                'p_error_message': error_message
            }).execute()
            self.logger.info(f"File marked as failed: {file_id}")
        except Exception as e:
            self.logger.error(f"Error marking file as failed: {e}")

    async def get_files_to_parse(
        self,
        bucket: str = 'raw-pdfs',
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get list of files ready for parsing.

        Args:
            bucket: Bucket name
            limit: Maximum number of files

        Returns:
            List of file records
        """
        try:
            response = self.client.rpc('get_files_to_parse', {
                'p_bucket': bucket,
                'p_limit': limit
            }).execute()

            return response.data if response.data else []

        except Exception as e:
            self.logger.error(f"Error getting files to parse: {e}")
            return []

    async def get_storage_statistics(self) -> List[Dict[str, Any]]:
        """Get storage usage statistics"""
        try:
            response = self.client.table('storage_statistics').select('*').execute()
            return response.data if response.data else []
        except Exception as e:
            self.logger.error(f"Error getting storage statistics: {e}")
            return []
