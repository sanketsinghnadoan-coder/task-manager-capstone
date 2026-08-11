"""
Quick-Add task parser: converts free-text task descriptions into structured records.

Implements deterministic (non-LLM) extraction rules for priority, due-date hints,
and cleaned titles — suitable for offline / free local use.
"""

from __future__ import annotations

import re
from typing import Optional, TypedDict


class ParsedTask(TypedDict):
    title: str
    priority: str  # "high" | "medium" | "low"
    due_date_hint: Optional[str]


# Priority keyword sets (case-insensitive substring match)
HIGH_PRIORITY_KEYWORDS = ("urgent", "asap")
LOW_PRIORITY_KEYWORDS = ("whenever", "low priority")

# Due-date phrases in explicit order of precedence (first match wins).
# Longer / more specific phrases must appear before bare weekdays.
DUE_DATE_PHRASES: tuple[str, ...] = (
    # 1. Relative dates
    "today",
    "tomorrow",
    "next week",
    # 2. Specific weekdays
    "next monday",
    "next tuesday",
    "next wednesday",
    "next thursday",
    "next friday",
    "next saturday",
    "next sunday",
    # 3. Bare weekdays
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def _extract_priority(text_lower: str) -> str:
    """Extract priority from free text using keyword rules."""
    has_high = any(kw in text_lower for kw in HIGH_PRIORITY_KEYWORDS)
    has_low = any(kw in text_lower for kw in LOW_PRIORITY_KEYWORDS)

    # If both high and low keywords exist, high wins
    if has_high:
        return "high"
    if has_low:
        return "low"
    return "medium"


def _extract_due_date_hint(text_lower: str) -> Optional[str]:
    """
    Search for date keywords using exact string matching in precedence order.
    Returns the first matched phrase in lowercase, or None.
    """
    for phrase in DUE_DATE_PHRASES:
        if phrase in text_lower:
            return phrase
    return None


def _remove_phrase_ci(text: str, phrase: str) -> str:
    """Remove the first case-insensitive occurrence of phrase from text."""
    pattern = re.compile(re.escape(phrase), re.IGNORECASE)
    return pattern.sub("", text, count=1)


def _clean_title(original: str, priority: str, due_date_hint: Optional[str]) -> str:
    """
    Remove matched priority keywords and date phrases, then strip
    leading/trailing whitespace and dangling punctuation.
    """
    title = original

    # Remove the due-date phrase that was matched (if any)
    if due_date_hint:
        title = _remove_phrase_ci(title, due_date_hint)

    # Remove all matching priority keywords present in the original text
    text_lower = original.lower()
    if priority == "high":
        for kw in HIGH_PRIORITY_KEYWORDS:
            if kw in text_lower:
                title = _remove_phrase_ci(title, kw)
    elif priority == "low":
        for kw in LOW_PRIORITY_KEYWORDS:
            if kw in text_lower:
                title = _remove_phrase_ci(title, kw)

    # Collapse whitespace
    title = re.sub(r"\s+", " ", title).strip()

    # Drop dangling connector fragments often left after keyword removal
    # e.g. "Finish the report , it's" → "Finish the report"
    title = re.sub(
        r"[,;:\-–—]\s*(it's|it is|its)?\s*$",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"\b(it's|it is)\s*$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip()

    # Strip leading/trailing non-word characters (dangling punctuation)
    title = re.sub(r"^[^\w]+|[^\w]+$", "", title)

    # Final whitespace collapse
    title = re.sub(r"\s+", " ", title).strip()

    if not title:
        return "Untitled task"
    return title


def parse_task_description(description: str) -> ParsedTask:
    """
    Convert a free-text task description into a structured record.

    Returns:
        {
          "title": str,
          "priority": "high" | "medium" | "low",
          "due_date_hint": str | None
        }
    """
    if description is None:
        description = ""

    text = str(description)
    text_lower = text.lower()

    priority = _extract_priority(text_lower)
    due_date_hint = _extract_due_date_hint(text_lower)
    title = _clean_title(text, priority, due_date_hint)

    return {
        "title": title,
        "priority": priority,
        "due_date_hint": due_date_hint,
    }
