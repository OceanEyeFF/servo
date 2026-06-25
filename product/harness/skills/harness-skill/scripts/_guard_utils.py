"""Shared YAML/Markdown parsing utilities for harness-skill guard scripts.

Usage:
    from _guard_utils import (
        parse_yaml_field, parse_bool_field, parse_int_field, field_present,
    )
"""

import re


def parse_yaml_field(content: str, field: str) -> str:
    """Extract a string field value from YAML content.

    Handles: single/double quotes, inline comments, trailing whitespace.
    """
    m = re.search(rf'{field}:\s*["\']?([^"\'#\n\r]+)', content)
    return m.group(1).strip() if m else ""


def parse_bool_field(content: str, field: str) -> bool | None:
    """Extract a boolean field from YAML content.

    Handles: true/false/True/False (case-insensitive), word boundary.
    """
    m = re.search(rf"{field}:\s*(true|false)\b", content, re.IGNORECASE)
    if m:
        return m.group(1).lower() == "true"
    return None


def parse_int_field(content: str, field: str) -> int | None:
    """Extract an integer field from YAML content."""
    m = re.search(rf"{field}:\s*(\d+)", content)
    if m:
        return int(m.group(1))
    return None


def field_present(content: str, field: str) -> bool:
    """Check if a field exists and has a meaningful (non-sentinel) value.

    Uses the same parsing logic as parse_yaml_field to avoid regex inconsistencies.
    """
    val = parse_yaml_field(content, field)
    if not val:
        return False
    return val.lower() not in ("null", "n/a", "none")
