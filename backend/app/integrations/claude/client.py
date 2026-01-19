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
# Using Opus 4.5 for better consistency in complex document extraction
CLAUDE_MODEL = "claude-opus-4-5-20250514"


def _repair_truncated_json(json_str: str) -> str | None:
    """
    Attempt to repair truncated JSON by closing open brackets/braces.

    This handles cases where Claude's response was cut off due to max_tokens.
    """
    # Count open brackets
    open_braces = json_str.count("{") - json_str.count("}")
    open_brackets = json_str.count("[") - json_str.count("]")

    if open_braces == 0 and open_brackets == 0:
        return None  # No repair needed or can't repair

    repaired = json_str.rstrip()

    # Remove trailing incomplete elements (after last comma in array/object)
    # This handles cases like: {"items": [{"a": 1}, {"b": 2
    if open_braces > 0 or open_brackets > 0:
        # Find last complete element
        last_complete = max(
            repaired.rfind("},"),
            repaired.rfind("],"),
            repaired.rfind('",'),
            repaired.rfind("0,"),
            repaired.rfind("1,"),
            repaired.rfind("2,"),
            repaired.rfind("3,"),
            repaired.rfind("4,"),
            repaired.rfind("5,"),
            repaired.rfind("6,"),
            repaired.rfind("7,"),
            repaired.rfind("8,"),
            repaired.rfind("9,"),
        )

        if last_complete > 0:
            # Keep up to and including the last complete element (without trailing comma)
            repaired = repaired[: last_complete + 1]
            if repaired.endswith(","):
                repaired = repaired[:-1]

    # Recount after trimming
    open_braces = repaired.count("{") - repaired.count("}")
    open_brackets = repaired.count("[") - repaired.count("]")

    # Close open brackets and braces
    repaired += "]" * open_brackets
    repaired += "}" * open_braces

    return repaired


def get_claude_client() -> anthropic.Anthropic:
    """Get Claude API client."""
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _log_extraction_summary(data: dict[str, Any], was_truncated: bool) -> None:
    """Log a summary of extracted data for debugging."""
    summary = {
        "document_type": data.get("document_type"),
        "was_truncated": was_truncated,
    }

    # Count items in each category
    if "transactions" in data:
        summary["transactions_count"] = len(data["transactions"])
    if "stock_positions" in data:
        summary["stock_positions_count"] = len(data["stock_positions"])
    if "fixed_income_positions" in data:
        summary["fixed_income_count"] = len(data["fixed_income_positions"])
    if "stock_lending" in data:
        summary["stock_lending_count"] = len(data["stock_lending"])
    if "derivatives_positions" in data:
        summary["derivatives_count"] = len(data["derivatives_positions"])
    if "cash_movements" in data and "movements" in data["cash_movements"]:
        summary["cash_movements_count"] = len(data["cash_movements"]["movements"])

    logger.info("extraction_summary", **summary)


async def parse_pdf_with_claude(
    pdf_content: bytes,
    prompt: str,
    max_tokens: int = 64000,
) -> dict[str, Any]:
    """
    Parse a PDF document using Claude's vision capabilities.

    Uses streaming to handle long-running requests (>10 minutes).

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
        max_tokens=max_tokens,
    )

    try:
        # Use streaming to handle long-running requests
        with client.messages.stream(
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
        ) as stream:
            # Collect the full response
            response_text = stream.get_final_text()
            message = stream.get_final_message()

        stop_reason = message.stop_reason

        # Check if response was truncated
        was_truncated = stop_reason == "max_tokens"

        logger.info(
            "claude_parse_response",
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            stop_reason=stop_reason,
            was_truncated=was_truncated,
            response_length=len(response_text),
        )

        if was_truncated:
            logger.warning(
                "claude_response_truncated",
                message="Response was truncated due to max_tokens limit. "
                "Some data may be missing. Consider increasing max_tokens.",
                output_tokens=message.usage.output_tokens,
                max_tokens=max_tokens,
            )

        # Parse JSON from response
        import json
        import re

        # Try to find JSON in the response
        json_str = response_text

        # Extract from markdown code block if present
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            if json_end == -1:
                json_end = len(response_text)
            json_str = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            if json_end == -1:
                json_end = len(response_text)
            json_str = response_text[json_start:json_end].strip()

        try:
            parsed_data = json.loads(json_str)
            _log_extraction_summary(parsed_data, was_truncated)
            return parsed_data
        except json.JSONDecodeError as e:
            logger.warning(
                "json_parse_error_attempting_repair",
                error=str(e),
                json_length=len(json_str),
                was_truncated=was_truncated,
            )

            # Try to repair truncated JSON
            repaired = _repair_truncated_json(json_str)
            if repaired:
                try:
                    parsed_data = json.loads(repaired)
                    logger.info(
                        "json_repair_success",
                        original_length=len(json_str),
                        repaired_length=len(repaired),
                    )
                    _log_extraction_summary(parsed_data, was_truncated)
                    return parsed_data
                except json.JSONDecodeError:
                    pass

            raise ValueError(
                f"Could not parse JSON from response: {response_text[:500]}..."
            )

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
