"""
Claude API client for document parsing.
"""

import base64
from typing import Any

import anthropic

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Claude model to use for document parsing
CLAUDE_MODEL = "claude-sonnet-4-20250514"


def get_claude_client() -> anthropic.Anthropic:
    """Get Claude API client."""
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


async def parse_pdf_with_claude(
    pdf_content: bytes,
    prompt: str,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """
    Parse a PDF document using Claude's vision capabilities.

    Args:
        pdf_content: PDF file content as bytes
        prompt: Prompt template for extraction
        max_tokens: Maximum tokens in response

    Returns:
        Parsed JSON data from Claude's response

    Raises:
        Exception: If parsing fails
    """
    client = get_claude_client()

    # Encode PDF as base64
    pdf_base64 = base64.standard_b64encode(pdf_content).decode("utf-8")

    logger.info(
        "claude_parse_start",
        pdf_size=len(pdf_content),
        model=CLAUDE_MODEL,
    )

    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )

        # Extract text response
        response_text = message.content[0].text

        logger.info(
            "claude_parse_success",
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )

        # Parse JSON from response
        import json

        # Try to find JSON in the response
        try:
            # First try direct parse
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
                return json.loads(json_str)
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
                return json.loads(json_str)
            else:
                raise ValueError(f"Could not parse JSON from response: {response_text[:500]}")

    except anthropic.APIError as e:
        logger.error(
            "claude_parse_api_error",
            error=str(e),
        )
        raise Exception(f"Claude API error: {str(e)}")
    except Exception as e:
        logger.error(
            "claude_parse_error",
            error=str(e),
        )
        raise
