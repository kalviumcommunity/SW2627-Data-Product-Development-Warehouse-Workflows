"""
Ingestion layer: reads and structurally validates the four raw source
files. None of these readers clean or transform values -- that's handled
separately, downstream.

Import from here rather than reaching into individual modules:

    from src.ingestion import read_all_sources
    sources = read_all_sources("data/raw")
    sources["prep_logs"]  # DataFrame
"""

from src.ingestion.complaints import read_complaints
from src.ingestion.packing_audits import read_packing_audits
from src.ingestion.prep_logs import read_prep_logs
from src.ingestion.read_all import read_all_sources
from src.ingestion.validation import MissingColumnsError, validate_columns
from src.ingestion.workflow_reference import read_workflow_reference

__all__ = [
    "read_prep_logs",
    "read_packing_audits",
    "read_complaints",
    "read_workflow_reference",
    "read_all_sources",
    "validate_columns",
    "MissingColumnsError",
]
