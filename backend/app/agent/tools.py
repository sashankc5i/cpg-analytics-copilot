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


MAX_PRODUCT_LIMIT = 50


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
                "Get stockout rates by region. "
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
}


def _validate_arguments(
    arguments,
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
        arguments
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