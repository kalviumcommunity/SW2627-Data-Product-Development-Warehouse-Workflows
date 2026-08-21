"""
Consolidated entry point for the ingestion layer.

Individually, prep_logs.py / packing_audits.py / complaints.py /
workflow_reference.py each read and validate one source file. This module
adds a single convenience function, read_all_sources(), that reads all
four from a directory in one call -- this is what the upcoming cleaning/
joining stage will actually import, rather than wiring up all four
individual readers itself every time.

If any one file is missing, has missing columns, or is empty, this fails
immediately and clearly names which file caused it -- the whole point of
validating structure at the ingestion boundary, applied consistently
across all four sources at once rather than one at a time.
"""

from pathlib import Path

import pandas as pd

from src.ingestion.complaints import read_complaints
from src.ingestion.packing_audits import read_packing_audits
from src.ingestion.prep_logs import read_prep_logs
from src.ingestion.workflow_reference import read_workflow_reference

FILENAMES = {
    "prep_logs": "prep_logs.csv",
    "packing_audits": "packing_audits.csv",
    "complaints": "complaints.csv",
    "workflow_reference": "workflow_reference.csv",
}


def read_all_sources(data_dir: Path) -> dict[str, pd.DataFrame]:
    """Read and validate all four raw sources from data_dir.

    Args:
        data_dir: directory containing prep_logs.csv, packing_audits.csv,
            complaints.csv, and workflow_reference.csv.

    Raises:
        FileNotFoundError: if any of the four files is missing.
        MissingColumnsError: if any file is missing an expected column.

    Returns:
        A dict keyed by source name ("prep_logs", "packing_audits",
        "complaints", "workflow_reference"), each value the raw
        (unmodified) DataFrame for that source.
    """
    data_dir = Path(data_dir)

    return {
        "prep_logs": read_prep_logs(data_dir / FILENAMES["prep_logs"]),
        "packing_audits": read_packing_audits(data_dir / FILENAMES["packing_audits"]),
        "complaints": read_complaints(data_dir / FILENAMES["complaints"]),
        "workflow_reference": read_workflow_reference(data_dir / FILENAMES["workflow_reference"]),
    }
