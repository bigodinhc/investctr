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

    @staticmethod
    def get_json_instruction() -> str:
        """Return standard JSON output instruction."""
        return """
IMPORTANT: Return ONLY valid JSON. Do not include any text before or after the JSON.
Do not wrap the JSON in markdown code blocks. Just return the raw JSON object.
"""
