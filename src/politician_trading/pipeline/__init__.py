"""
Modular ingestion pipeline for politician trading disclosures.

The pipeline consists of four stages:
1. Ingest - Fetch raw data from sources
2. Clean - Validate and clean raw data
3. Normalize - Transform into standard format
4. Publish - Store in database

Each stage can be run independently or as part of a full pipeline.
"""

from .base import (
    PipelineStage,
    PipelineResult,
    PipelineContext,
    PipelineError
)
from .ingest import IngestionStage
from .clean import CleaningStage
from .normalize import NormalizationStage
from .publish import PublishingStage
from .orchestrator import PipelineOrchestrator

__all__ = [
    'PipelineStage',
    'PipelineResult',
    'PipelineContext',
    'PipelineError',
    'IngestionStage',
    'CleaningStage',
    'NormalizationStage',
    'PublishingStage',
    'PipelineOrchestrator'
]
