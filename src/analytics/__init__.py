"""
Analytics layer: aggregates the combined table into the metrics
operations leads actually want to see -- complaint counts and failure
rate, by workflow (and eventually by station).
"""

from src.analytics.failure_rate import UNKNOWN_WORKFLOW_LABEL, complaints_and_failure_rate_by_workflow

__all__ = [
    "complaints_and_failure_rate_by_workflow",
    "UNKNOWN_WORKFLOW_LABEL",
]
