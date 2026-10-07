"""Prompt-injection guardrails: PR content is wrapped as data, output is validated."""

import re

from pydantic import ValidationError

from app.agent.schemas import Finding

OPEN, CLOSE = "<untrusted_pr_content", "</untrusted_pr_content>"
# Any spelling of the tag inside content (case, spaces, attributes) is neutralised.
ANY_TAG = re.compile(r"<\s*/?\s*untrusted_pr_content[^>]*>", re.IGNORECASE)

SUBMIT_TOOL = {
    "type": "function",
    "name": "submit_findings",
    "description": "Finish the review: call once with every finding (an empty list is fine).",
    "parameters": {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "file": {"type": "string"},
                        "line": {"type": "integer"},
                        "category": {"type": "string", "enum": ["bug", "security", "missing_test"]},
                        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                        "confidence": {"type": "number"},
                        "explanation": {"type": "string"},
                    },
                    "required": [
                        "file",
                        "line",
                        "category",
                        "severity",
                        "confidence",
                        "explanation",
                    ],
                },
            }
        },
        "required": ["findings"],
    },
}


def wrap_untrusted(label: str, text: str) -> str:
    # Content can't end the block early: any delimiter-like tag inside it is defused.
    safe = ANY_TAG.sub("[tag removed]", text)
    return f'{OPEN} part="{label}">\n{safe}\n{CLOSE}'


def parse_submission(arguments: dict) -> tuple[list[Finding], int]:
    """Validate each submitted finding on its own; returns (valid findings, number dropped)."""
    items = arguments.get("findings")
    if not isinstance(items, list):
        return [], 1
    valid = []
    for item in items:
        try:
            valid.append(Finding.model_validate(item))
        except ValidationError:
            continue
    return valid, len(items) - len(valid)
