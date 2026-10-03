from app.agent.clarification import (
    build_clarification_response,
)


def test_clarifies_sales_performance_without_period():
    result = build_clarification_response(
        "How did sales perform?"
    )

    assert result is not None
    assert "period" in result.lower()


def test_clarifies_revenue_improvement_without_comparison():
    result = build_clarification_response(
        "Did revenue improve?"
    )

    assert result is not None
    assert "compare" in result.lower()


def test_does_not_clarify_explicit_period():
    result = build_clarification_response(
        "How did sales perform last month?"
    )

    assert result is None


def test_does_not_clarify_explicit_comparison():
    result = build_clarification_response(
        "Did revenue improve compared with last month?"
    )

    assert result is None


def test_does_not_clarify_specific_revenue_question():
    result = build_clarification_response(
        "What is our total revenue?"
    )

    assert result is None


def test_does_not_clarify_specific_region_question():
    result = build_clarification_response(
        "What was our revenue in the South region?"
    )

    assert result is None
from app.agent.clarification import (
    build_clarification_response,
)


def test_how_are_sales_performing_requires_clarification():
    result = build_clarification_response(
        "How are sales performing?"
    )

    assert result is not None
    assert "period" in result.lower()


def test_how_did_sales_perform_requires_clarification():
    result = build_clarification_response(
        "How did sales perform?"
    )

    assert result is not None
    assert "period" in result.lower()


def test_how_are_our_sales_performing_requires_clarification():
    result = build_clarification_response(
        "How are our sales performing?"
    )

    assert result is not None
    assert "period" in result.lower()


def test_sales_performance_with_last_month_does_not_clarify():
    result = build_clarification_response(
        "How did sales perform last month?"
    )

    assert result is None


def test_sales_performance_with_comparison_does_not_clarify():
    result = build_clarification_response(
        "How did sales perform compared to last month?"
    )

    assert result is None