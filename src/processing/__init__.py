"""
Processing layer: cleans raw ingested data (fixing/flagging missing or
malformed values) and, later, joins the four sources into one combined
table. Cleaning never drops rows -- it flags problems so later stages
can decide how to handle them.
"""

from src.processing.clean_prep_logs import clean_prep_logs

__all__ = ["clean_prep_logs"]
