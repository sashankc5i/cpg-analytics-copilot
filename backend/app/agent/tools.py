import json

from app.analytics.filters import normalize_filters
from app.analytics.sales import (
    get_overall_sales,
    get_sales_by_region,
    get_monthly_sales_trend,
)
from app.analytics.products import (
    get_top_products,
    get_sales_by_category,
)
from app.analytics.customers import (
    get_customer_segment_performance,
)
from app.analytics.promotions import (
    get_promotion_impact,
)
from app.analytics.inventory import (
    get_stockout_rate,
)
from app.analytics.anomalies import (
    get_revenue_anomalies,
)
from app.analytics.variance_analysis import (
    get_sales_variance,
)
from app.analytics.drilldown import (
    get_hierarchical_drilldown,
)
from app.analytics.data_quality import (
    get_data_quality_indicators,
)
from app.analytics.freshness import (
    get_data_freshness,
)
from app.analytics.investigation_drivers import (
    get_driver_decomposition,
    get_contribution_analysis,
)


MAX_PRODUCT_LIMIT = 50


STOCKOUT_FILTER_SCHEMA = {
    "type": "object",
    "description": (
        "Optional region filter. Stockout rate currently supports "
        "region only; date, category, brand, and customer segment "
        "filters are not supported by this metric."
    ),
    "properties": {
        "region": {
            "oneOf": [
                {"type": "string"},
                {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 10,
                },
            ]
        }
    },
    "additionalProperties": False,
}


FILTER_SCHEMA = {
    "type": "object",
    "description": (
        "Optional governed filters for narrowing the "
        "analytics result."
    ),
    "properties": {
        "start_date": {
            "type": "string",
            "description": (
                "Start date in YYYY-MM-DD format."
            ),
        },
        "end_date": {
            "type": "string",
            "description": (
                "End date in YYYY-MM-DD format."
            ),
        },
        "region": {
            "type": "array",
            "description": (
                "One or more regions to include."
            ),
            "items": {
                "type": "string",
            },
        },
        "category": {
            "type": "array",
            "description": (
                "One or more product categories to include."
            ),
            "items": {
                "type": "string",
            },
        },
        "brand": {
            "type": "array",
            "description": (
                "One or more brands to include."
            ),
            "items": {
                "type": "string",
            },
        },
        "customer_segment": {
            "type": "array",
            "description": (
                "One or more customer segments to include."
            ),
            "items": {
                "type": "string",
            },
        },
    },
    "additionalProperties": False,
}


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_overall_sales",
            "description": (
                "Get overall CPG sales performance "
                "including transactions, units sold, "
                "revenue, and average transaction value. "
                "Supports optional filters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filters": FILTER_SCHEMA,
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_by_region",
            "description": (
                "Get sales performance broken down "
                "by region. Supports optional filters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filters": FILTER_SCHEMA,
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_monthly_sales_trend",
            "description": (
                "Get monthly sales trends including "
                "revenue, transactions, and units sold. "
                "Supports optional filters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filters": FILTER_SCHEMA,
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_products",
            "description": (
                "Get the top performing products by "
                "revenue. Supports optional filters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": (
                            "Number of products to return. "
                            "Must be between 1 and 50."
                        ),
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                    },
                    "filters": FILTER_SCHEMA,
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_by_category",
            "description": (
                "Get sales performance by product "
                "category. Supports optional filters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filters": FILTER_SCHEMA,
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_segment_performance",
            "description": (
                "Get sales performance by customer "
                "segment. Supports optional filters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filters": FILTER_SCHEMA,
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_promotion_impact",
            "description": (
                "Compare sales transactions with and "
                "without promotions. Supports optional "
                "filters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filters": FILTER_SCHEMA,
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stockout_rate",
            "description": (
                "Get stockout rates by region. Supports an optional "
                "region filter only. Date, category, brand, and "
                "customer segment filters are not supported."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filters": STOCKOUT_FILTER_SCHEMA,
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_revenue_anomalies",
            "description": (
                "Detect unusual monthly revenue movements "
                "using a historical three-month baseline. "
                "Returns only months with a significant "
                "revenue deviation, including actual revenue, "
                "expected revenue, deviation percentage, "
                "direction, and severity. Supports optional "
                "filters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filters": FILTER_SCHEMA,
                },
                "required": [],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "get_sales_variance",
            "description": (
                "Compare a governed sales metric between a current "
                "period and a comparison period. Returns current "
                "value, comparison value, absolute change, "
                "percentage change, and direction. Supports "
                "previous period, previous month, and year-over-year "
                "comparisons. If the current period is not provided, "
                "the latest available sales month is used. "
                "Supports optional governed filters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_id": {
                        "type": "string",
                        "enum": [
                            "revenue",
                            "transactions",
                            "units_sold",
                            "average_transaction_value",
                        ],
                        "description": "Governed metric to compare.",
                    },
                    "current_start": {
                        "type": "string",
                        "description": (
                            "Optional start date of the current analytical "
                            "period in YYYY-MM-DD format."
                        ),
                    },
                    "current_end": {
                        "type": "string",
                        "description": (
                            "Optional end date of the current analytical "
                            "period in YYYY-MM-DD format."
                        ),
                    },
                    "comparison_type": {
                        "type": "string",
                        "enum": [
                            "previous_period",
                            "previous_month",
                            "year_over_year",
                        ],
                        "description": "Comparison period to use.",
                    },
                    "filters": FILTER_SCHEMA,
                },
                "required": [
                    "metric_id",
                    "comparison_type",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_hierarchical_drilldown",
            "description": (
                "Drill down through the CPG analytical hierarchy "
                "from company to region, category, or product. "
                "Preserves governed filters for the selected scope."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {
                        "type": "string",
                        "enum": [
                            "company",
                            "region",
                            "category",
                            "product",
                        ],
                        "description": "Hierarchy level to retrieve.",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                        "description": "Maximum number of product results.",
                    },
                    "filters": FILTER_SCHEMA,
                },
                "required": ["level"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_quality_indicators",
            "description": (
                "Surface deterministic data-quality indicators across "
                "the CPG dataset, including missing values, duplicate "
                "keys, referential integrity issues, and invalid sales values."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_driver_decomposition",
            "description": (
                "Decompose a governed metric change between a current "
                "period and comparison period by region, category, or "
                "product. Returns driver-level current value, comparison "
                "value, absolute change, and direction."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_id": {
                        "type": "string",
                        "enum": [
                            "revenue",
                            "transactions",
                            "units_sold",
                        ],
                    },
                    "current_start": {"type": "string"},
                    "current_end": {"type": "string"},
                    "comparison_type": {
                        "type": "string",
                        "enum": [
                            "previous_period",
                            "previous_month",
                            "year_over_year",
                        ],
                        "default": "previous_period",
                    },
                    "level": {
                        "type": "string",
                        "enum": [
                            "region",
                            "category",
                            "product",
                        ],
                        "default": "region",
                    },
                    "filters": FILTER_SCHEMA,
                },
                "required": [
                    "metric_id",
                    "current_start",
                    "current_end",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_contribution_analysis",
            "description": (
                "Quantify each region, category, or product's contribution "
                "to the total change of a governed sales metric."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_id": {
                        "type": "string",
                        "enum": [
                            "revenue",
                            "transactions",
                            "units_sold",
                        ],
                    },
                    "current_start": {"type": "string"},
                    "current_end": {"type": "string"},
                    "comparison_type": {
                        "type": "string",
                        "enum": [
                            "previous_period",
                            "previous_month",
                            "year_over_year",
                        ],
                        "default": "previous_period",
                    },
                    "level": {
                        "type": "string",
                        "enum": [
                            "region",
                            "category",
                            "product",
                        ],
                        "default": "region",
                    },
                    "filters": FILTER_SCHEMA,
                },
                "required": [
                    "metric_id",
                    "current_start",
                    "current_end",
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_freshness",
            "description": (
                "Show deterministic data freshness metadata based on "
                "the latest available data date for each source table. "
                "The application does not currently store physical "
                "ingestion timestamps."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
]


AVAILABLE_FUNCTIONS = {
    "get_overall_sales": get_overall_sales,
    "get_sales_by_region": get_sales_by_region,
    "get_monthly_sales_trend": get_monthly_sales_trend,
    "get_top_products": get_top_products,
    "get_sales_by_category": get_sales_by_category,
    "get_customer_segment_performance": (
        get_customer_segment_performance
    ),
    "get_promotion_impact": get_promotion_impact,
    "get_stockout_rate": get_stockout_rate,
    "get_revenue_anomalies": get_revenue_anomalies,
    "get_sales_variance": get_sales_variance,
    "get_hierarchical_drilldown": get_hierarchical_drilldown,
    "get_data_quality_indicators": get_data_quality_indicators,
    "get_data_freshness": get_data_freshness,
    "get_driver_decomposition": get_driver_decomposition,
    "get_contribution_analysis": get_contribution_analysis,
}


def _validate_arguments(
    arguments,
    tool_name: str | None = None,
) -> dict:
    """
    Validate and normalize tool arguments.

    Tool arguments originate from an LLM and therefore
    must not be trusted to have the expected structure.

    Tools currently accept JSON objects only.
    """

    if arguments is None:
        return {}

    if not isinstance(arguments, dict):
        raise ValueError(
            "Tool arguments must be a JSON object."
        )

    validated_arguments = dict(arguments)

    if "filters" in validated_arguments:
        filters = validated_arguments["filters"]

        if filters is not None:
            if not isinstance(filters, dict):
                raise ValueError(
                    "Tool argument 'filters' must be an object."
                )

            validated_arguments["filters"] = (
                normalize_filters(filters)
            )

    if tool_name == "get_stockout_rate":
        filters = validated_arguments.get("filters") or {}
        unsupported = sorted(
            key for key in filters
            if key != "region"
        )
        if unsupported:
            raise ValueError(
                "Stockout rate currently supports only the region "
                "filter. Unsupported filters: "
                + ", ".join(unsupported)
            )

    return validated_arguments


def execute_tool(
    tool_name: str,
    arguments: dict | None,
):
    """
    Execute an approved analytics tool.

    The function name must exist in AVAILABLE_FUNCTIONS
    and arguments must be a dictionary.

    All validated arguments are passed to the approved
    analytics function. The LLM never generates SQL.
    """

    if tool_name not in AVAILABLE_FUNCTIONS:
        raise ValueError(
            f"Unknown tool: {tool_name}"
        )

    validated_arguments = _validate_arguments(
        arguments,
        tool_name=tool_name,
    )

    function = AVAILABLE_FUNCTIONS[tool_name]

    if tool_name == "get_top_products":
        limit = validated_arguments.get(
            "limit",
            10,
        )

        if isinstance(limit, bool) or not isinstance(
            limit,
            int,
        ):
            raise ValueError(
                "Product limit must be an integer."
            )

        if (
            limit < 1
            or limit > MAX_PRODUCT_LIMIT
        ):
            raise ValueError(
                "Product limit must be between "
                "1 and 50."
            )

        filters = validated_arguments.get(
            "filters"
        )

        return function(
            limit=limit,
            filters=filters,
        )

    if tool_name == "get_sales_variance":
        return function(
            metric_id=validated_arguments["metric_id"],
            current_start=validated_arguments.get("current_start"),
            current_end=validated_arguments.get("current_end"),
            comparison_type=validated_arguments["comparison_type"],
            filters=validated_arguments.get("filters"),
        )

    if tool_name == "get_hierarchical_drilldown":
        return function(
            level=validated_arguments["level"],
            limit=validated_arguments.get("limit", 10),
            filters=validated_arguments.get("filters"),
        )

    if tool_name in {
        "get_data_quality_indicators",
        "get_data_freshness",
    }:
        return function()

    if tool_name in {
        "get_driver_decomposition",
        "get_contribution_analysis",
    }:
        return function(
            metric_id=validated_arguments["metric_id"],
            current_start=validated_arguments["current_start"],
            current_end=validated_arguments["current_end"],
            comparison_type=validated_arguments.get(
                "comparison_type",
                "previous_period",
            ),
            level=validated_arguments.get(
                "level",
                "region",
            ),
            filters=validated_arguments.get("filters"),
        )

    filters = validated_arguments.get(
        "filters"
    )

    return function(
        filters=filters,
    )


def execute_tool_as_json(
    tool_name: str,
    arguments: dict | None,
):
    """
    Execute an approved analytics tool and serialize
    the result as JSON.
    """

    result = execute_tool(
        tool_name,
        arguments,
    )

    return json.dumps(
        result,
        default=str,
    )