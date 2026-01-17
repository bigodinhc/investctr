"""
Celery tasks for background processing.
"""

from .parse_document import parse_document

__all__ = [
    "parse_document",
]
