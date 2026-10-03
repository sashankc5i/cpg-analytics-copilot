from datetime import date

import pytest

from app.analytics.filters import (
    build_sales_filter_sql,
    normalize_filters,
)


class TestNormalizeFilters:
    def test_empty_filters(self):
        assert normalize_filters(None) == {}
        assert normalize_filters({}) == {}

    def test_valid_scalar_values_are_normalized_to_lists(self):
        filters = normalize_filters(
            {
                "region": "South",
                "category": "Personal Care",
                "brand": "Nexa",
                "customer_segment": "Premium",
            }
        )

        assert filters == {
            "region": ["South"],
            "category": ["Personal Care"],
            "brand": ["Nexa"],
            "customer_segment": ["Premium"],
        }

    def test_valid_list_values_are_preserved(self):
        filters = normalize_filters(
            {
                "region": ["South", "West"],
                "category": ["Personal Care", "Food"],
            }
        )

        assert filters == {
            "region": ["South", "West"],
            "category": ["Personal Care", "Food"],
        }

    def test_dates_are_preserved(self):
        filters = normalize_filters(
            {
                "start_date": "2026-01-01",
                "end_date": "2026-03-31",
            }
        )

        assert filters == {
            "start_date": "2026-01-01",
            "end_date": "2026-03-31",
        }

    def test_unknown_filter_is_rejected(self):
        with pytest.raises(ValueError, match="Unsupported filters"):
            normalize_filters(
                {
                    "region": "South",
                    "unknown_filter": "something",
                }
            )

    def test_invalid_date_is_rejected(self):
        with pytest.raises(
            ValueError,
            match="valid YYYY-MM-DD date",
        ):
            normalize_filters(
                {
                    "start_date": "2026-99-99",
                }
            )

    def test_non_string_date_is_rejected(self):
        with pytest.raises(
            ValueError,
            match="YYYY-MM-DD string",
        ):
            normalize_filters(
                {
                    "start_date": date(2026, 1, 1),
                }
            )

    def test_reversed_date_range_is_rejected(self):
        with pytest.raises(
            ValueError,
            match="start_date.*on or before",
        ):
            normalize_filters(
                {
                    "start_date": "2026-04-01",
                    "end_date": "2026-03-31",
                }
            )

    def test_empty_string_is_rejected(self):
        with pytest.raises(
            ValueError,
            match="non-empty strings",
        ):
            normalize_filters(
                {
                    "region": "",
                }
            )

    def test_too_many_values_are_rejected(self):
        with pytest.raises(
            ValueError,
            match="at most 10 values",
        ):
            normalize_filters(
                {
                    "region": [
                        "Region 1",
                        "Region 2",
                        "Region 3",
                        "Region 4",
                        "Region 5",
                        "Region 6",
                        "Region 7",
                        "Region 8",
                        "Region 9",
                        "Region 10",
                        "Region 11",
                    ]
                }
            )


class TestBuildSalesFilterSQL:
    def test_no_filters_returns_empty_where_clause(self):
        sql, params, needs_store, needs_product, needs_customer = (
            build_sales_filter_sql({})
        )

        assert sql == ""
        assert params == []
        assert needs_store is False
        assert needs_product is False
        assert needs_customer is False

    def test_region_filter(self):
        sql, params, needs_store, needs_product, needs_customer = (
            build_sales_filter_sql(
                {
                    "region": "South",
                }
            )
        )

        assert "st.region IN (?)" in sql
        assert params == ["South"]
        assert needs_store is True
        assert needs_product is False
        assert needs_customer is False

    def test_multiple_regions(self):
        sql, params, needs_store, needs_product, needs_customer = (
            build_sales_filter_sql(
                {
                    "region": ["South", "West"],
                }
            )
        )

        assert "st.region IN (?, ?)" in sql
        assert params == ["South", "West"]
        assert needs_store is True
        assert needs_product is False
        assert needs_customer is False

    def test_category_filter(self):
        sql, params, needs_store, needs_product, needs_customer = (
            build_sales_filter_sql(
                {
                    "category": "Personal Care",
                }
            )
        )

        assert "p.category IN (?)" in sql
        assert params == ["Personal Care"]
        assert needs_store is False
        assert needs_product is True
        assert needs_customer is False

    def test_brand_filter(self):
        sql, params, needs_store, needs_product, needs_customer = (
            build_sales_filter_sql(
                {
                    "brand": "Nexa",
                }
            )
        )

        assert "p.brand IN (?)" in sql
        assert params == ["Nexa"]
        assert needs_store is False
        assert needs_product is True
        assert needs_customer is False

    def test_customer_segment_filter(self):
        sql, params, needs_store, needs_product, needs_customer = (
            build_sales_filter_sql(
                {
                    "customer_segment": "Premium",
                }
            )
        )

        assert "c.customer_segment IN (?)" in sql
        assert params == ["Premium"]
        assert needs_store is False
        assert needs_product is False
        assert needs_customer is True

    def test_date_range(self):
        sql, params, needs_store, needs_product, needs_customer = (
            build_sales_filter_sql(
                {
                    "start_date": "2026-01-01",
                    "end_date": "2026-03-31",
                }
            )
        )

        assert (
            "DATE(s.transaction_date) >= DATE(?)"
            in sql
        )

        assert (
            "DATE(s.transaction_date) <= DATE(?)"
            in sql
        )

        assert params == [
            "2026-01-01",
            "2026-03-31",
        ]

        assert needs_store is False
        assert needs_product is False
        assert needs_customer is False

    def test_combined_filters(self):
        sql, params, needs_store, needs_product, needs_customer = (
            build_sales_filter_sql(
                {
                    "region": "South",
                    "category": "Personal Care",
                    "brand": "Nexa",
                    "customer_segment": "Premium",
                    "start_date": "2026-01-01",
                    "end_date": "2026-03-31",
                }
            )
        )

        assert "st.region IN (?)" in sql
        assert "p.category IN (?)" in sql
        assert "p.brand IN (?)" in sql
        assert "c.customer_segment IN (?)" in sql
        assert "DATE(s.transaction_date) >= DATE(?)" in sql
        assert "DATE(s.transaction_date) <= DATE(?)" in sql

        assert params == [
            "2026-01-01",
            "2026-03-31",
            "South",
            "Personal Care",
            "Nexa",
            "Premium",
        ]

        assert needs_store is True
        assert needs_product is True
        assert needs_customer is True

    def test_custom_date_column(self):
        sql, params, _, _, _ = build_sales_filter_sql(
            {
                "start_date": "2026-01-01",
            },
            date_column="s.sale_date",
        )

        assert (
            "DATE(s.sale_date) >= DATE(?)"
            in sql
        )

        assert params == ["2026-01-01"]