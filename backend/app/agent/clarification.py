import re


COMPARISON_MARKERS = (
    "vs",
    "versus",
    "compared with",
    "compared to",
    "against",
    "previous month",
    "prior month",
    "last month",
    "previous period",
    "prior period",
    "last period",
    "year over year",
    "yoy",
    "benchmark",
)


PERFORMANCE_PATTERN = re.compile(
    r"\bhow\s+"
    r"(?:did|has|have|is|are)"
    r"\s+"
    r"(?:our\s+)?"
    r"sales"
    r"\s+"
    r"(?:perform|performed|performing)\b",
    re.IGNORECASE,
)


IMPROVEMENT_PATTERN = re.compile(
    r"\b(?:did|has|have|is|are)\s+"
    r"(?:our\s+)?"
    r"(sales|revenue)"
    r"\s+"
    r"(?:improve|increase|grow|decline|decrease|change|"
    r"perform better|perform worse)\b",
    re.IGNORECASE,
)


def _has_comparison_context(text: str) -> bool:
    normalized = text.lower()

    return any(
        marker in normalized
        for marker in COMPARISON_MARKERS
    )


def build_clarification_response(
    user_message: str,
) -> str | None:
    """
    Determine whether the current question requires clarification.

    This gate runs before the LLM so genuinely ambiguous analytical
    questions cannot be answered by guessing from conversation context.

    The function is intentionally conservative:
    - explicit comparison questions are allowed through
    - specific analytical questions are allowed through
    - ambiguous sales/revenue performance questions require
      the missing comparison period or benchmark
    """

    text = user_message.strip()

    if not text:
        return None

    # An explicit comparison already provides the missing analytical
    # reference point, so no clarification is required.
    if _has_comparison_context(text):
        return None

    # "How did/has/is/are sales perform?" is ambiguous because
    # performance requires a comparison period or benchmark.
    if PERFORMANCE_PATTERN.search(text):
        return (
            "What period should I use for the sales performance "
            "analysis—for example, this month, last month, or "
            "a specific date range?"
        )

    # Revenue/sales improvement questions also require a comparison
    # point unless one was explicitly provided.
    if IMPROVEMENT_PATTERN.search(text):
        return (
            "What should I compare the revenue performance "
            "against—for example, the previous month, previous "
            "period, or another benchmark?"
        )

    return None