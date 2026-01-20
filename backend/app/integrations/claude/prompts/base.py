"""
Base prompt template for document parsing.
"""

from abc import ABC, abstractmethod
from typing import Any


class BasePrompt(ABC):
    """Abstract base class for document parsing prompts."""

    @property
    @abstractmethod
    def prompt_template(self) -> str:
        """Return the prompt template string."""
        pass

    @property
    @abstractmethod
    def document_type(self) -> str:
        """Return the document type identifier."""
        pass

    def get_prompt(self, **kwargs: Any) -> str:
        """
        Get the formatted prompt with optional parameters.

        Args:
            **kwargs: Optional parameters to format into the template

        Returns:
            Formatted prompt string
        """
        template = self.prompt_template
        if kwargs:
            template = template.format(**kwargs)
        return template

    def get_focused_prompt(self, sections: list[str]) -> str | None:
        """
        Return a focused prompt for extracting specific sections.

        Override in subclasses to provide section-specific retry prompts.

        Args:
            sections: List of section names to extract

        Returns:
            Focused prompt string or None if not available
        """
        return None

    @staticmethod
    def get_json_instruction() -> str:
        """Return standard JSON output instruction."""
        return """
IMPORTANT OUTPUT RULES:
1. Return ONLY valid JSON. Do not include any text before or after the JSON.
2. Do not wrap the JSON in markdown code blocks. Just return the raw JSON object.
3. Keep values concise - use null instead of empty strings or "N/A".
4. For notes/descriptions, be brief (max 50 chars).
5. CRITICAL: Ensure the JSON is COMPLETE. Do not truncate the output.
6. If the document has many transactions (50+), prioritize the most important ones.
"""
