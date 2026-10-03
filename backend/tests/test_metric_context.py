from app.agent.agent import (
    _update_metric_context_from_message,
)


def build_context():
    return {
        "metric": None,
        "filters": {},
        "date_range": {
            "start_date": None,
            "end_date": None,
        },
        "comparison_period": None,
        "selected_entity": None,
        "active_investigation": None,
        "last_tool": None,
    }


def test_revenue_updates_metric_context():
    context = build_context()

    updated = _update_metric_context_from_message(
        context=context,
        user_message="What is our revenue?",
    )

    assert updated["metric"] == {
        "id": "revenue",
        "display_name": "Revenue",
    }


def test_units_sold_updates_metric_context():
    context = build_context()

    updated = _update_metric_context_from_message(
        context=context,
        user_message="How many units were sold?",
    )

    assert updated["metric"] == {
        "id": "units_sold",
        "display_name": "Units Sold",
    }


def test_transactions_update_metric_context():
    context = build_context()

    updated = _update_metric_context_from_message(
        context=context,
        user_message="How many transactions did we have?",
    )

    assert updated["metric"] == {
        "id": "transactions",
        "display_name": "Transactions",
    }


def test_ambiguous_sales_message_does_not_guess_metric():
    context = build_context()

    updated = _update_metric_context_from_message(
        context=context,
        user_message="How are sales performing?",
    )

    assert updated["metric"] is None


def test_follow_up_without_metric_preserves_existing_metric():
    context = build_context()

    context["metric"] = {
        "id": "revenue",
        "display_name": "Revenue",
    }

    updated = _update_metric_context_from_message(
        context=context,
        user_message="What about North?",
    )

    assert updated["metric"] == {
        "id": "revenue",
        "display_name": "Revenue",
    }


def test_explicit_metric_change_replaces_existing_metric():
    context = build_context()

    context["metric"] = {
        "id": "revenue",
        "display_name": "Revenue",
    }

    updated = _update_metric_context_from_message(
        context=context,
        user_message="What about units sold?",
    )

    assert updated["metric"] == {
        "id": "units_sold",
        "display_name": "Units Sold",
    }


def test_metric_resolution_does_not_modify_original_context():
    context = build_context()

    updated = _update_metric_context_from_message(
        context=context,
        user_message="What is our revenue?",
    )

    assert context["metric"] is None

    assert updated["metric"] == {
        "id": "revenue",
        "display_name": "Revenue",
    }


def test_other_context_is_preserved():
    context = build_context()

    context["filters"] = {
        "region": ["South"],
    }

    context["date_range"] = {
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
    }

    updated = _update_metric_context_from_message(
        context=context,
        user_message="What is the revenue?",
    )

    assert updated["metric"] == {
        "id": "revenue",
        "display_name": "Revenue",
    }

    assert updated["filters"] == {
        "region": ["South"],
    }

    assert updated["date_range"] == {
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
    }