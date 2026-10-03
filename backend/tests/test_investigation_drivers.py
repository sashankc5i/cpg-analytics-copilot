import app.analytics.investigation_drivers as drivers


def test_driver_decomposition_builds_absolute_changes(monkeypatch):
    def fake_rows(level, filters):
        if filters["start_date"] == "2026-09-01":
            return [{"region": "South", "revenue": 120}, {"region": "North", "revenue": 80}]
        return [{"region": "South", "revenue": 100}, {"region": "North", "revenue": 100}]

    monkeypatch.setattr(drivers, "_rows_for_level", fake_rows)
    result = drivers.get_driver_decomposition(
        metric_id="revenue",
        current_start="2026-09-01",
        current_end="2026-09-30",
        comparison_type="previous_month",
        level="region",
    )
    assert result["total_change"] == 0.0
    assert {item["entity"] for item in result["drivers"]} == {"South", "North"}
    assert next(item for item in result["drivers"] if item["entity"] == "South")["absolute_change"] == 20.0


def test_contribution_analysis_ranks_by_absolute_change(monkeypatch):
    monkeypatch.setattr(
        drivers,
        "get_driver_decomposition",
        lambda **kwargs: {
            "metric": "revenue",
            "level": "region",
            "total_change": 50.0,
            "drivers": [
                {"entity": "A", "absolute_change": 40.0},
                {"entity": "B", "absolute_change": 10.0},
            ],
        },
    )
    result = drivers.get_contribution_analysis(
        metric_id="revenue",
        current_start="2026-09-01",
        current_end="2026-09-30",
    )
    assert result["drivers"][0]["entity"] == "A"
    assert result["drivers"][0]["contribution_percentage"] == 80.0
