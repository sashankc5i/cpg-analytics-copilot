# Data Model

## 1. Overview

The CPG Analytics Copilot uses a relational data model representing the core business operations of a fictional Consumer Packaged Goods (CPG) company, **Nexa Consumer Products**.

The model is designed to support business questions across:

* Sales
* Products
* Customers
* Stores
* Regions
* Promotions
* Inventory

The current implementation uses **SQLite** as the transactional analytical store.

The primary transactional table is `sales`, while the remaining entities provide dimensions and supporting operational information.

---

# 2. Data Model Overview

The logical model can be represented as:

```text
                         ┌──────────────────┐
                         │    Customers     │
                         │                  │
                         │ customer_id PK   │
                         │ segment          │
                         │ city             │
                         │ state            │
                         └────────┬─────────┘
                                  │
                                  │ customer_id
                                  │
                                  ▼
                         ┌──────────────────┐
                         │      Sales       │
                         │                  │
                         │ transaction_id PK│
                         │ transaction_date │
                         │ customer_id FK   │
                         │ product_id FK    │
                         │ store_id FK      │
                         │ quantity         │
                         │ unit_price      │
                         │ discount        │
                         │ sales_amount    │
                         └───────┬───┬──────┘
                                 │   │
                   product_id ───┘   └─── store_id
                         │                 │
                         ▼                 ▼
                ┌────────────────┐  ┌────────────────┐
                │    Products    │  │     Stores     │
                │                │  │                │
                │ product_id PK  │  │ store_id PK    │
                │ product_name   │  │ store_name     │
                │ category       │  │ city           │
                │ subcategory    │  │ state          │
                │ brand          │  │ region         │
                │ unit_price     │  │ store_type     │
                │ cost           │  │                │
                └───────┬────────┘  └───────┬────────┘
                        │                   │
                        ├───────┐   ┌───────┤
                        │       │   │       │
                        ▼       ▼   ▼       ▼
                ┌────────────────┐  ┌────────────────┐
                │  Promotions    │  │   Inventory    │
                │                │  │                │
                │ promotion_id PK│  │ inventory_id PK│
                │ product_id FK  │  │ product_id FK  │
                │ store_id FK    │  │ store_id FK    │
                │ promotion_type │  │ inventory_date │
                │ start_date     │  │ opening_stock  │
                │ end_date       │  │ closing_stock  │
                │ discount_pct   │  │ stockout_flag  │
                └────────────────┘  └────────────────┘
```

---

# 3. Entity Overview

The database contains six primary entities:

| Entity       | Purpose                   | Role            |
| ------------ | ------------------------- | --------------- |
| `customers`  | Customer master data      | Dimension       |
| `products`   | Product master data       | Dimension       |
| `stores`     | Store and geographic data | Dimension       |
| `sales`      | Customer transactions     | Primary fact    |
| `promotions` | Promotion campaigns       | Supporting fact |
| `inventory`  | Daily inventory state     | Supporting fact |

---

# 4. Customers

## Table

```text
customers
```

The `customers` table contains customer master information.

## Schema

| Column              | Type    | Description                 |
| ------------------- | ------- | --------------------------- |
| `customer_id`       | INTEGER | Primary key                 |
| `customer_name`     | TEXT    | Customer name               |
| `gender`            | TEXT    | Customer gender             |
| `age_group`         | TEXT    | Age grouping                |
| `city`              | TEXT    | Customer city               |
| `state`             | TEXT    | Customer state              |
| `customer_segment`  | TEXT    | Premium, Standard, or Value |
| `registration_date` | DATE    | Customer registration date  |

## Primary Key

```text
customer_id
```

## Business Purpose

Customer information supports analysis such as:

* segment performance
* customer distribution
* revenue by segment
* transaction behavior
* customer-level analysis

---

# 5. Customer Segments

The synthetic dataset uses three customer segments:

```text
Premium
Standard
Value
```

These segments are used to simulate differences in customer purchasing behavior.

Conceptually:

```text
Customers
    │
    ├── Premium
    │
    ├── Standard
    │
    └── Value
```

This allows the analytics layer to answer questions such as:

```text
How are our customer segments performing?
```

---

# 6. Products

## Table

```text
products
```

The `products` table contains product master data.

## Schema

| Column         | Type    | Description         |
| -------------- | ------- | ------------------- |
| `product_id`   | INTEGER | Primary key         |
| `product_name` | TEXT    | Product name        |
| `category`     | TEXT    | Product category    |
| `subcategory`  | TEXT    | Product subcategory |
| `brand`        | TEXT    | Brand               |
| `unit_price`   | REAL    | Standard unit price |
| `cost`         | REAL    | Product cost        |

## Primary Key

```text
product_id
```

## Business Purpose

Products enable analysis across:

* product performance
* category performance
* brand performance
* revenue contribution
* unit sales

---

# 7. Product Categories

The synthetic business contains three primary categories:

```text
Personal Care
Home Care
Food & Beverages
```

The relationship is:

```text
Product
   │
   └── Category
```

This supports questions such as:

```text
Which category generates the most revenue?
```

and:

```text
Which categories are contributing to a revenue decline?
```

---

# 8. Stores

## Table

```text
stores
```

The `stores` table represents retail and distribution locations.

## Schema

| Column       | Type    | Description        |
| ------------ | ------- | ------------------ |
| `store_id`   | INTEGER | Primary key        |
| `store_name` | TEXT    | Store name         |
| `city`       | TEXT    | City               |
| `state`      | TEXT    | State              |
| `region`     | TEXT    | Business region    |
| `store_type` | TEXT    | Channel/store type |

## Primary Key

```text
store_id
```

## Regions

The synthetic data contains four regions:

```text
South
West
North
East
```

The region is derived from the associated state.

Example:

```text
Tamil Nadu
     ↓
South
```

---

# 9. Store Types

The model represents four primary channels:

```text
Supermarket
Convenience
E-commerce
Distributor
```

These allow the system to represent different commercial channels.

The store type can later be used to support questions such as:

```text
Which channel contributes the most revenue?
```

Although channel-specific analytics are not currently exposed as a dedicated agent tool.

---

# 10. Sales

## Table

```text
sales
```

The `sales` table is the primary transactional fact table.

## Schema

| Column             | Type    | Description                         |
| ------------------ | ------- | ----------------------------------- |
| `transaction_id`   | INTEGER | Primary key                         |
| `transaction_date` | DATE    | Transaction date                    |
| `customer_id`      | INTEGER | Customer foreign key                |
| `product_id`       | INTEGER | Product foreign key                 |
| `store_id`         | INTEGER | Store foreign key                   |
| `quantity`         | INTEGER | Units purchased                     |
| `unit_price`       | REAL    | Transaction unit price              |
| `discount`         | REAL    | Discount amount/rate representation |
| `sales_amount`     | REAL    | Transaction revenue                 |

---

# 11. Sales Relationships

The sales table connects the primary business dimensions.

```text
Customers
     │
     │ customer_id
     ▼
   Sales
     │
     ├──────── product_id ────────► Products
     │
     └──────── store_id ──────────► Stores
```

This creates the central analytical model.

For example:

```text
Sales
  +
Products
```

can answer:

```text
Which products generate the most revenue?
```

While:

```text
Sales
  +
Stores
```

can answer:

```text
Which region performs best?
```

And:

```text
Sales
  +
Customers
```

can answer:

```text
Which customer segment generates the most revenue?
```

---

# 12. Revenue Definition

The primary revenue metric is based on:

```text
sales.sales_amount
```

Overall revenue is calculated as:

```sql
SUM(sales_amount)
```

The analytics layer rounds the resulting value for presentation.

The LLM does not independently calculate or invent revenue values.

---

# 13. Units Sold

Units sold are represented by:

```text
sales.quantity
```

Overall units are calculated as:

```sql
SUM(quantity)
```

Regional and product-level unit metrics are calculated by grouping the sales records.

---

# 14. Transaction Count

Each row in the `sales` table represents a transaction.

Transaction count is therefore calculated using:

```sql
COUNT(*)
```

This supports metrics such as:

```text
Total transactions
Transactions by region
Transactions by customer segment
Promotion transactions
```

---

# 15. Average Transaction Value

Average transaction value is calculated using:

```sql
AVG(sales_amount)
```

This provides an additional measure beyond total revenue.

For example, two regions could have similar revenue but different:

```text
Transaction count
+
Average transaction value
```

This distinction can be useful for business analysis.

---

# 16. Promotions

## Table

```text
promotions
```

The `promotions` table represents promotional activity associated with products and stores.

## Schema

| Column                | Type    | Description          |
| --------------------- | ------- | -------------------- |
| `promotion_id`        | INTEGER | Primary key          |
| `product_id`          | INTEGER | Product foreign key  |
| `store_id`            | INTEGER | Store foreign key    |
| `promotion_type`      | TEXT    | Promotion type       |
| `start_date`          | DATE    | Promotion start      |
| `end_date`            | DATE    | Promotion end        |
| `discount_percentage` | REAL    | Promotional discount |

---

# 17. Promotion Analysis

The current promotion analytics tool determines promotion status using the sales discount field.

Conceptually:

```text
discount > 0
      ↓
Promotion

discount = 0
      ↓
No Promotion
```

The tool compares:

```text
Promotion
vs.
No Promotion
```

across metrics including:

* transaction count
* units sold
* average quantity
* revenue
* average transaction value

This provides descriptive analysis.

It does **not** establish causal promotional effectiveness.

---

# 18. Inventory

## Table

```text
inventory
```

The inventory table represents inventory conditions by product, store, and date.

## Schema

| Column           | Type    | Description         |
| ---------------- | ------- | ------------------- |
| `inventory_id`   | INTEGER | Primary key         |
| `product_id`     | INTEGER | Product foreign key |
| `store_id`       | INTEGER | Store foreign key   |
| `inventory_date` | DATE    | Inventory date      |
| `opening_stock`  | INTEGER | Opening inventory   |
| `closing_stock`  | INTEGER | Closing inventory   |
| `stockout_flag`  | INTEGER | Indicates stockout  |

The `stockout_flag` is represented as:

```text
0 = No stockout
1 = Stockout
```

---

# 19. Stockout Rate

The regional stockout rate is calculated as:

```text
Stockout Rate
=
Stockout Events / Inventory Records
× 100
```

The analytics layer calculates this deterministically.

Example:

```text
Region
Inventory Records
Stockout Events
Stockout Rate
```

This supports questions such as:

```text
Are we having stockouts?
```

---

# 20. Foreign Key Relationships

The major relationships are:

```text
customers.customer_id
        │
        └──── sales.customer_id


products.product_id
        │
        ├──── sales.product_id
        ├──── promotions.product_id
        └──── inventory.product_id


stores.store_id
        │
        ├──── sales.store_id
        ├──── promotions.store_id
        └──── inventory.store_id
```

These relationships provide referential structure across the analytical model.

---

# 21. Indexing Strategy

The schema includes indexes on frequently queried fields.

## Sales

```text
idx_sales_date
idx_sales_product
idx_sales_store
idx_sales_customer
```

These support common analytical filters and joins.

## Inventory

```text
idx_inventory_product_store
idx_inventory_date
```

These support product/store analysis and date-based inventory analysis.

## Promotions

```text
idx_promotions_product
idx_promotions_dates
```

These support product and date-based promotional queries.

---

# 22. Analytical Query Patterns

The model primarily supports aggregation and dimensional analysis.

## Overall Sales

```text
Sales
  ↓
Aggregate
  ↓
Revenue
Units
Transactions
Average Transaction Value
```

## Regional Sales

```text
Sales
  ↓
JOIN Stores
  ↓
GROUP BY Region
```

## Product Sales

```text
Sales
  ↓
JOIN Products
  ↓
GROUP BY Product
```

## Category Sales

```text
Sales
  ↓
JOIN Products
  ↓
GROUP BY Category
```

## Customer Segment Sales

```text
Sales
  ↓
JOIN Customers
  ↓
GROUP BY Customer Segment
```

## Inventory Analysis

```text
Inventory
  ↓
JOIN Stores
  ↓
GROUP BY Region
  ↓
Stockout Rate
```

---

# 23. Data Generation

The current database is populated using synthetic data.

Approximate dataset sizes are:

```text
Customers     10,000
Products         100
Stores           200
Promotions       300
Inventory    100,000
Sales        250,000
```

The generator uses a fixed random seed:

```python
random.seed(42)
```

This makes the synthetic dataset reproducible.

---

# 24. Synthetic Business Logic

The data generator introduces controlled business variation.

## Customer Segments

```text
Premium
Standard
Value
```

Different purchasing multipliers are applied to simulate different spending behavior.

## Store Types

```text
Supermarket
Convenience
E-commerce
Distributor
```

Different sales multipliers simulate different commercial volumes.

## Regions

```text
South
West
North
East
```

Regional multipliers introduce variation across geographies.

## Promotions

Promotional transactions can receive higher quantities to simulate promotional lift.

## Inventory

Inventory records include a synthetic stockout probability.

---

# 25. Data Quality and Reconciliation

The project includes deterministic data integrity tests.

Regional revenue must reconcile with overall revenue:

```text
SUM(regional revenue)
=
overall revenue
```

Regional units must reconcile with overall units:

```text
SUM(regional units)
=
overall units
```

These tests help ensure that dimensional analytical queries are consistent with overall metrics.

---

# 26. Known Data Modeling Limitations

The current model is intentionally simplified for training purposes.

### 1. Synthetic data

The dataset does not represent real customer or business data.

### 2. SQLite

SQLite is suitable for local development but is not intended as the final enterprise production database.

### 3. Inventory-sales relationship

The synthetic sales generator does not currently enforce inventory availability.

Therefore, a stockout record does not necessarily prevent a corresponding sales transaction.

This means stockout analysis should be interpreted as an observational analytical signal rather than a direct causal measurement.

### 4. Promotion modeling

Promotional lookup during data generation is currently implemented with a simple lookup approach and could be optimized for larger datasets.

### 5. Limited dimensionality

The current model does not yet include dedicated entities for:

* suppliers
* warehouses
* territories
* sales representatives
* pricing history
* returns
* orders
* shipments

These could be introduced in a future enterprise version.

---

# 27. Future Production Data Architecture

A production version could migrate the model from SQLite to Azure SQL.

Conceptually:

```text
                    Azure SQL
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
     Customer       Product         Store
        │              │              │
        └──────────────┼──────────────┘
                       ▼
                     Sales
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
        Promotions           Inventory
```

Additional enterprise data could be integrated through:

* Azure Data Factory
* Databricks
* Azure Functions
* event-driven ingestion
* enterprise APIs
* operational databases

---

# 28. Relationship to the Analytics Agent

The data model is intentionally hidden behind analytics tools.

The agent does not need to understand every table directly.

Instead:

```text
User
 ↓
Agent
 ↓
Analytics Tool
 ↓
Data Model
 ↓
Query
 ↓
Result
```

For example:

```text
User:
"Which region performs best?"
```

The agent selects:

```text
get_sales_by_region
```

The tool internally understands that this requires:

```text
sales
+
stores
```

The user and LLM therefore interact with business capabilities rather than raw database implementation details.

---

# 29. FDE Perspective

From an FDE perspective, the data model represents the **enterprise system boundary behind the AI experience**.

The important design principle is:

> **Expose business capabilities to the agent rather than exposing raw infrastructure.**

Instead of asking the LLM to understand:

```text
sales.store_id
stores.region
sales.sales_amount
```

the system exposes:

```text
get_sales_by_region()
```

This provides a cleaner abstraction:

```text
Business Question
       ↓
Business Capability
       ↓
Data Model
       ↓
Deterministic Query
       ↓
Business Result
```

This makes the system easier to evolve.

If the underlying database changes from:

```text
SQLite
```

to:

```text
Azure SQL
```

the agent does not necessarily need to change.

The analytics tool can retain the same business-facing contract while its implementation changes underneath.

---

# 30. Data Model Mental Model

The simplest way to understand the model is:

```text
                         BUSINESS
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
          Customers      Products       Stores
              │             │             │
              └─────────────┼─────────────┘
                            │
                            ▼
                           Sales
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
            Promotions             Inventory
```

And analytically:

```text
                   Sales Fact
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
     Product        Customer        Store
        │              │              │
        └──────────────┼──────────────┘
                       ▼
                  Business Metrics
                       │
                       ▼
                 Analytics Tools
                       │
                       ▼
                    AI Agent
```

The data model therefore forms the deterministic foundation underneath the conversational analytics layer.

---

# 31. Summary

The CPG Analytics Copilot uses a relational model centered around the `sales` transaction table and supported by customer, product, store, promotion, and inventory entities.

The model provides the foundation for:

* revenue analysis
* regional analysis
* product analysis
* category analysis
* customer segment analysis
* promotion analysis
* inventory analysis

The architecture deliberately separates:

```text
Data Model
    ↓
Deterministic Analytics
    ↓
Analytics Tools
    ↓
AI Agent
```

This separation ensures that the conversational interface can evolve independently from the underlying data implementation while maintaining deterministic and testable business logic.
