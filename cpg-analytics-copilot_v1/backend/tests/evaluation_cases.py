EVALUATION_CASES = [
    {
        "id": "EV001",
        "question": "What is our total revenue?",
        "expected_tools": ["get_overall_sales"],
        "category": "simple_lookup",
    },
    {
        "id": "EV002",
        "question": "Which region performs best?",
        "expected_tools": ["get_sales_by_region"],
        "category": "regional_analysis",
    },
    {
        "id": "EV003",
        "question": "What are our top 10 products?",
        "expected_tools": ["get_top_products"],
        "category": "product_analysis",
    },
    {
        "id": "EV004",
        "question": "Show me monthly revenue.",
        "expected_tools": ["get_monthly_sales_trend"],
        "category": "trend_analysis",
    },
    {
        "id": "EV005",
        "question": "How are our customer segments performing?",
        "expected_tools": [
            "get_customer_segment_performance"
        ],
        "category": "customer_analysis",
    },
    {
        "id": "EV006",
        "question": "Do promotions work?",
        "expected_tools": ["get_promotion_impact"],
        "category": "promotion_analysis",
    },
    {
        "id": "EV007",
        "question": "Are we having stockouts?",
        "expected_tools": ["get_stockout_rate"],
        "category": "inventory_analysis",
    },
    {
        "id": "EV008",
        "question": "Why is revenue changing?",
        "expected_tools": [
            "get_monthly_sales_trend",
            "get_sales_by_region",
            "get_top_products",
        ],
        "category": "diagnostic_analysis",
    },
]