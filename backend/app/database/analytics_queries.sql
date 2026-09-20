SELECT 'customers' AS table_name, COUNT(*) AS record_count
FROM customers

UNION ALL

SELECT 'products', COUNT(*)
FROM products

UNION ALL

SELECT 'stores', COUNT(*)
FROM stores

UNION ALL

SELECT 'promotions', COUNT(*)
FROM promotions

UNION ALL

SELECT 'inventory', COUNT(*)
FROM inventory

UNION ALL

SELECT 'sales', COUNT(*)
FROM sales;

SELECT
    COUNT(*) AS transaction_count,
    SUM(quantity) AS total_units,
    ROUND(SUM(sales_amount), 2) AS total_revenue,
    ROUND(AVG(sales_amount), 2) AS average_transaction_value
FROM sales;

SELECT
    st.region,
    COUNT(*) AS transactions,
    SUM(s.quantity) AS units_sold,
    ROUND(SUM(s.sales_amount), 2) AS revenue
FROM sales s
JOIN stores st
    ON s.store_id = st.store_id
GROUP BY st.region
ORDER BY revenue DESC;

SELECT
    st.state,
    COUNT(*) AS transactions,
    SUM(s.quantity) AS units_sold,
    ROUND(SUM(s.sales_amount), 2) AS revenue
FROM sales s
JOIN stores st
    ON s.store_id = st.store_id
GROUP BY st.state
ORDER BY revenue DESC;

SELECT
    p.category,
    COUNT(*) AS transactions,
    SUM(s.quantity) AS units_sold,
    ROUND(SUM(s.sales_amount), 2) AS revenue
FROM sales s
JOIN products p
    ON s.product_id = p.product_id
GROUP BY p.category
ORDER BY revenue DESC;

SELECT
    p.product_id,
    p.product_name,
    p.category,
    p.brand,
    SUM(s.quantity) AS units_sold,
    ROUND(SUM(s.sales_amount), 2) AS revenue
FROM sales s
JOIN products p
    ON s.product_id = p.product_id
GROUP BY
    p.product_id,
    p.product_name,
    p.category,
    p.brand
ORDER BY revenue DESC
LIMIT 10;

SELECT
    c.customer_segment,
    COUNT(*) AS transactions,
    COUNT(DISTINCT c.customer_id) AS customers,
    SUM(s.quantity) AS units_sold,
    ROUND(SUM(s.sales_amount), 2) AS revenue,
    ROUND(AVG(s.sales_amount), 2) AS avg_transaction_value
FROM sales s
JOIN customers c
    ON s.customer_id = c.customer_id
GROUP BY c.customer_segment
ORDER BY revenue DESC;

SELECT
    st.store_type,
    COUNT(*) AS transactions,
    SUM(s.quantity) AS units_sold,
    ROUND(SUM(s.sales_amount), 2) AS revenue,
    ROUND(AVG(s.sales_amount), 2) AS avg_transaction_value
FROM sales s
JOIN stores st
    ON s.store_id = st.store_id
GROUP BY st.store_type
ORDER BY revenue DESC;

SELECT
    strftime('%Y-%m', transaction_date) AS month,
    COUNT(*) AS transactions,
    SUM(quantity) AS units_sold,
    ROUND(SUM(sales_amount), 2) AS revenue
FROM sales
GROUP BY month
ORDER BY month;

SELECT
    CASE
        WHEN discount > 0 THEN 'Promotion'
        ELSE 'No Promotion'
    END AS promotion_status,

    COUNT(*) AS transactions,

    SUM(quantity) AS units_sold,

    ROUND(AVG(quantity), 2) AS avg_quantity,

    ROUND(SUM(sales_amount), 2) AS revenue,

    ROUND(AVG(sales_amount), 2) AS avg_transaction_value

FROM sales

GROUP BY promotion_status;

SELECT
    p.product_name,
    COUNT(*) AS promotional_transactions,
    SUM(s.quantity) AS units_sold,
    ROUND(SUM(s.sales_amount), 2) AS revenue,
    ROUND(AVG(s.discount), 2) AS avg_discount
FROM sales s
JOIN products p
    ON s.product_id = p.product_id
WHERE s.discount > 0
GROUP BY
    p.product_id,
    p.product_name
ORDER BY revenue DESC
LIMIT 10;

SELECT
    st.region,
    COUNT(*) AS inventory_records,
    SUM(i.stockout_flag) AS stockout_events,
    ROUND(
        100.0 * SUM(i.stockout_flag) / COUNT(*),
        2
    ) AS stockout_rate
FROM inventory i
JOIN stores st
    ON i.store_id = st.store_id
GROUP BY st.region
ORDER BY stockout_rate DESC;

SELECT
    p.product_name,
    COUNT(*) AS inventory_records,
    SUM(i.stockout_flag) AS stockout_events,
    ROUND(
        100.0 * SUM(i.stockout_flag) / COUNT(*),
        2
    ) AS stockout_rate
FROM inventory i
JOIN products p
    ON i.product_id = p.product_id
GROUP BY
    p.product_id,
    p.product_name
ORDER BY stockout_rate DESC
LIMIT 10;

