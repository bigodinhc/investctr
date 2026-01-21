"""
Prompt templates for Claude document parsing.
"""

from .base import BasePrompt
from .statement import BTGStatementPrompt
from .statement_cayman import BTGCaymanStatementPrompt
from .trade_note import BTGTradeNotePrompt

__all__ = [
    "BasePrompt",
    "BTGStatementPrompt",
    "BTGCaymanStatementPrompt",
    "BTGTradeNotePrompt",
]
