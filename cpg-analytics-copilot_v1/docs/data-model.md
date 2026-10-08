# Nexa Analytics Copilot --- Data Model

## 1. Purpose

Nexa Analytics Copilot uses a synthetic CPG dataset designed to support
conversational business analytics and investigation workflows.

The data model represents six core business domains:

``` text
Customers
Products
Stores
Sales
Promotions
Inventory
```

The model is intentionally relational so that analytical questions can
combine commercial, customer, product, store, promotion, and inventory
information.

------------------------------------------------------------------------

# 2. Logical Data Model

``` text
┌─────────────────┐
│   customers     │
│─────────────────│
│ customer_id PK  │
│ customer_name   │
│ gender          │
│ age_group       │
│ city            │
│ state           │
│ segment         │
│ registration    │
└────────┬────────┘
         │
         │ customer_id
         │
         ▼
┌─────────────────┐
│      sales      │
│─────────────────│
│ transaction_id  │
│ transaction_date│
│ customer_id FK  │
│ product_id FK   │
│ store_id FK     │
│ quantity        │
│ unit_price      │
│ discount        │
│ sales_amount    │
└───────┬────┬────┘
        │    │
        │    │
        │    └──────────────────┐
        │                       │
        ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│    products     │     │     stores      │
│─────────────────│     │─────────────────│
│ product_id PK   │     │ store_id PK     │
│ product_name    │     │ store_name      │
│ category        │     │ city            │
│ subcategory     │     │ state           │
│ brand           │     │ region          │
│ unit_price      │     │ store_type      │
│ cost            │     └────────┬────────┘
└───────┬─────────┘              │
        │                        │
        │ product_id             │ store_id
        │                        │
        ▼                        ▼
┌─────────────────┐     ┌─────────────────┐
│  promotions     │     │   inventory     │
│─────────────────│     │─────────────────│
│ promotion_id PK │     │ inventory_id PK │
│ product_id FK   │     │ product_id FK   │
│ store_id FK     │     │ store_id FK     │
│ promotion_type  │     │ inventory_date  │
│ start_date      │     │ opening_stock   │
│ end_date        │     │ closing_stock   │
│ discount_pct    │     │ stockout_flag   │
└─────────────────┘     └─────────────────┘
```

------------------------------------------------------------------------

# 3. Database Tables

## 3.1 `customers`

The customer table represents the customer dimension.

``` sql
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    customer_name TEXT NOT NULL,
    gender TEXT,
    age_group TEXT,
    city TEXT,
    state TEXT,
    customer_segment TEXT,
    registration_date DATE
);
```

### Columns

  Column                Type      Description
  --------------------- --------- -------------------------------------
  `customer_id`         INTEGER   Unique customer identifier
  `customer_name`       TEXT      Customer display name
  `gender`              TEXT      Synthetic customer gender attribute
  `age_group`           TEXT      Customer age grouping
  `city`                TEXT      Customer city
  `state`               TEXT      Customer state
  `customer_segment`    TEXT      Premium, Standard, or Value
  `registration_date`   DATE      Customer registration date

### Analytical use

Customer attributes support analyses such as:

-   Customer segment performance
-   Revenue by customer segment
-   Customer behavior comparisons
-   Segment-level business performance

------------------------------------------------------------------------

# 4. `products`

The product table represents the product dimension.

``` sql
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    brand TEXT NOT NULL,
    unit_price REAL NOT NULL,
    cost REAL NOT NULL
);
```

### Columns

  Column           Type      Description
  ---------------- --------- ---------------------------
  `product_id`     INTEGER   Unique product identifier
  `product_name`   TEXT      Product name
  `category`       TEXT      Product category
  `subcategory`    TEXT      Product subcategory
  `brand`          TEXT      Product brand
  `unit_price`     REAL      Base product price
  `cost`           REAL      Product cost

### Categories

The synthetic dataset contains:

-   Personal Care
-   Home Care
-   Food & Beverages

### Brands

The generated products use:

-   Nexa
-   PureLife
-   FreshDay
-   UrbanChoice
-   DailyPlus

### Analytical use

Products support:

-   Top-product analysis
-   Category performance
-   Brand comparisons
-   Product-level revenue analysis
-   Promotion analysis
-   Inventory analysis

------------------------------------------------------------------------

# 5. `stores`

The store table represents physical and digital sales locations.

``` sql
CREATE TABLE IF NOT EXISTS stores (
    store_id INTEGER PRIMARY KEY,
    store_name TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    region TEXT NOT NULL,
    store_type TEXT NOT NULL
);
```

### Columns

  -----------------------------------------------------------------------
  Column                  Type                    Description
  ----------------------- ----------------------- -----------------------
  `store_id`              INTEGER                 Unique store identifier

  `store_name`            TEXT                    Store name

  `city`                  TEXT                    Store city

  `state`                 TEXT                    Store state

  `region`                TEXT                    Business region

  `store_type`            TEXT                    Supermarket,
                                                  Convenience,
                                                  E-commerce, or
                                                  Distributor
  -----------------------------------------------------------------------

### Regions

The synthetic geography is organized into:

  Region   States
  -------- ------------------------------------------
  South    Tamil Nadu, Karnataka, Kerala, Telangana
  West     Maharashtra, Gujarat
  North    Rajasthan, Delhi, Uttar Pradesh
  East     West Bengal

### Analytical use

Stores enable:

-   Regional performance analysis
-   Store-type analysis
-   Geographic comparisons
-   Revenue by region
-   Inventory analysis by location

------------------------------------------------------------------------

# 6. `sales`

The sales table is the central transactional fact table.

``` sql
CREATE TABLE IF NOT EXISTS sales (
    transaction_id INTEGER PRIMARY KEY,
    transaction_date DATE NOT NULL,
    customer_id INTEGER,
    product_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    discount REAL DEFAULT 0,
    sales_amount REAL NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (store_id) REFERENCES stores(store_id)
);
```

### Columns

  Column               Type      Description
  -------------------- --------- --------------------------------------
  `transaction_id`     INTEGER   Unique transaction identifier
  `transaction_date`   DATE      Transaction date
  `customer_id`        INTEGER   Customer associated with transaction
  `product_id`         INTEGER   Product sold
  `store_id`           INTEGER   Store/location where sale occurred
  `quantity`           INTEGER   Units sold
  `unit_price`         REAL      Price used for the transaction
  `discount`           REAL      Discount applied
  `sales_amount`       REAL      Resulting transaction sales value

### Analytical role

Sales is the primary source for:

-   Revenue
-   Transaction counts
-   Units sold
-   Product performance
-   Regional performance
-   Category performance
-   Customer segment performance
-   Monthly trends
-   Revenue anomalies

The `sales_amount` field is treated as the transaction-level revenue
measure used by the analytical layer.

------------------------------------------------------------------------

# 7. `promotions`

The promotion table represents promotional campaigns associated with
products and, optionally, stores.

``` sql
CREATE TABLE IF NOT EXISTS promotions (
    promotion_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    store_id INTEGER,
    promotion_type TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    discount_percentage REAL NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (store_id) REFERENCES stores(store_id)
);
```

### Columns

  Column                  Type      Description
  ----------------------- --------- -----------------------------------
  `promotion_id`          INTEGER   Unique promotion identifier
  `product_id`            INTEGER   Product affected by promotion
  `store_id`              INTEGER   Optional store-specific promotion
  `promotion_type`        TEXT      Promotion classification
  `start_date`            DATE      Promotion start
  `end_date`              DATE      Promotion end
  `discount_percentage`   REAL      Promotion discount percentage

### Analytical use

Promotions support:

-   Promotion impact analysis
-   Product promotion comparisons
-   Discount-related sales analysis
-   Investigation hypotheses around changing sales

Promotion analysis should be interpreted as an observed relationship in
the synthetic data rather than automatic proof of causation.

------------------------------------------------------------------------

# 8. `inventory`

The inventory table represents inventory observations by product and
store.

``` sql
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    inventory_date DATE NOT NULL,
    opening_stock INTEGER NOT NULL,
    closing_stock INTEGER NOT NULL,
    stockout_flag INTEGER DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (store_id) REFERENCES stores(store_id)
);
```

### Columns

  Column             Type      Description
  ------------------ --------- --------------------------------
  `inventory_id`     INTEGER   Unique inventory record
  `product_id`       INTEGER   Product being tracked
  `store_id`         INTEGER   Store being tracked
  `inventory_date`   DATE      Inventory observation date
  `opening_stock`    INTEGER   Stock at beginning of period
  `closing_stock`    INTEGER   Stock at end of period
  `stockout_flag`    INTEGER   Indicates a stockout condition

### Analytical use

Inventory supports:

-   Stockout-rate analysis
-   Product/store availability analysis
-   Investigation of potential supply-side constraints

------------------------------------------------------------------------

# 9. Relationships

## Customer → Sales

``` text
customers.customer_id
        │
        ▼
sales.customer_id
```

A customer can be associated with multiple sales transactions.

The `customer_id` in `sales` is nullable, allowing transactions without
an associated customer.

------------------------------------------------------------------------

## Product → Sales

``` text
products.product_id
        │
        ▼
sales.product_id
```

A product can appear in many sales transactions.

------------------------------------------------------------------------

## Store → Sales

``` text
stores.store_id
        │
        ▼
sales.store_id
```

A store can have many sales transactions.

------------------------------------------------------------------------

## Product → Promotions

``` text
products.product_id
        │
        ▼
promotions.product_id
```

A product can participate in multiple promotions.

------------------------------------------------------------------------

## Store → Promotions

``` text
stores.store_id
        │
        ▼
promotions.store_id
```

A promotion can optionally be associated with a specific store.

The nullable `store_id` allows promotions that are not tied to one
store.

------------------------------------------------------------------------

## Product → Inventory

``` text
products.product_id
        │
        ▼
inventory.product_id
```

A product can have multiple inventory observations.

------------------------------------------------------------------------

## Store → Inventory

``` text
stores.store_id
        │
        ▼
inventory.store_id
```

A store can have inventory observations for multiple products and dates.

------------------------------------------------------------------------

# 10. Indexing Strategy

The schema creates indexes for the most common analytical access paths.

``` sql
CREATE INDEX IF NOT EXISTS idx_sales_date
ON sales(transaction_date);

CREATE INDEX IF NOT EXISTS idx_sales_product
ON sales(product_id);

CREATE INDEX IF NOT EXISTS idx_sales_store
ON sales(store_id);

CREATE INDEX IF NOT EXISTS idx_sales_customer
ON sales(customer_id);

CREATE INDEX IF NOT EXISTS idx_inventory_product_store
ON inventory(product_id, store_id);

CREATE INDEX IF NOT EXISTS idx_inventory_date
ON inventory(inventory_date);

CREATE INDEX IF NOT EXISTS idx_promotions_product
ON promotions(product_id);

CREATE INDEX IF NOT EXISTS idx_promotions_dates
ON promotions(start_date, end_date);
```

### Why these indexes exist

The analytics layer frequently filters or groups by:

-   Date
-   Product
-   Store
-   Customer
-   Product/store inventory combinations
-   Promotion date ranges

The indexes support these access patterns without exposing arbitrary SQL
execution to the agent.

------------------------------------------------------------------------

# 11. Synthetic Dataset

The dataset is generated specifically for development, testing, and
demonstration.

Approximate generated volumes:

  Domain         Records
  ------------ ---------
  Customers       10,000
  Products           100
  Stores             200
  Promotions         300
  Inventory      100,000
  Sales          250,000

The generator uses:

``` python
random.seed(42)
```

This makes the generated dataset deterministic and reproducible.

------------------------------------------------------------------------

# 12. Synthetic Business Dimensions

## Customer Segments

The generator uses three customer segments:

  Segment      Approx. distribution   Relative multiplier
  ---------- ---------------------- ---------------------
  Premium                       15%                  1.60
  Standard                      55%                  1.00
  Value                         30%                  0.70

These multipliers influence synthetic purchasing behavior.

They should not be interpreted as real-world customer economics.

------------------------------------------------------------------------

## Store Types

The generated store types include:

  Store type      Relative multiplier
  ------------- ---------------------
  Supermarket                    1.30
  Convenience                    0.80
  E-commerce                     1.15
  Distributor                    1.50

These are synthetic generation parameters used to create variation in
the dataset.

------------------------------------------------------------------------

## Regional Multipliers

The synthetic generator uses:

  Region     Multiplier
  -------- ------------
  South            1.15
  West             1.20
  North            1.00
  East             0.90

Again, these are generation parameters rather than claims about actual
market performance.

------------------------------------------------------------------------

# 13. Promotion Simulation

Promotions are represented in the generated data and can influence
synthetic quantity generation.

The generator applies a quantity boost within a synthetic range when an
applicable promotion is present.

The project uses promotion data to support analytical questions such as:

``` text
Did promoted products sell differently?
Which products had promotional activity?
How does promotion performance compare?
```

Promotion impact should be treated as an analytical relationship
observed in the generated dataset.

------------------------------------------------------------------------

# 14. Inventory Simulation

Inventory records contain:

-   Opening stock
-   Closing stock
-   Stockout flag

The generator uses a synthetic stockout probability of approximately 5%.

The current sales generator does **not** constrain sales based on
inventory stockouts.

Therefore:

``` text
Inventory stockout
        ≠
Guaranteed lost sale
```

The stockout data is currently useful for investigation and analytical
demonstration, but the dataset does not model a fully causal
inventory-to-sales relationship.

This is an intentional known limitation of the current synthetic
generator.

------------------------------------------------------------------------

# 15. Analytical Model

The data model supports several analytical paths.

## Revenue

``` text
sales
  │
  └── sales_amount
          │
          ▼
       Revenue
```

## Regional Performance

``` text
sales
  │
  └── store_id
          │
          ▼
        stores
          │
          └── region
```

## Product Performance

``` text
sales
  │
  └── product_id
          │
          ▼
       products
          │
          ├── product_name
          ├── category
          └── brand
```

## Customer Segment Performance

``` text
sales
  │
  └── customer_id
          │
          ▼
      customers
          │
          └── customer_segment
```

## Promotion Impact

``` text
products
    │
    ├── sales
    │
    └── promotions
```

## Inventory Stockouts

``` text
products
    │
    └── inventory
            │
            └── stores
```

------------------------------------------------------------------------

# 16. Data Access Boundary

The data model is intentionally hidden behind repository interfaces.

The application flow is:

``` text
Agent
  ↓
Tools
  ↓
Analytics
  ↓
Repositories
  ↓
SQLite
```

The LLM does not receive direct access to:

-   SQLite connections
-   Arbitrary SQL
-   Database schema execution
-   Unrestricted query generation

This is important because the analytical model should remain controlled
by the application rather than being dynamically redefined by the LLM.

------------------------------------------------------------------------

# 17. Data Quality Considerations

The synthetic dataset is suitable for demonstrating analytical
workflows, but it should not be treated as production-quality business
data.

Important considerations include:

-   Synthetic customer identities
-   Synthetic transactions
-   Synthetic regional behavior
-   Synthetic promotion effects
-   Synthetic inventory observations
-   No real customer privacy concerns
-   No external business truth represented by the generated values

The purpose of the dataset is to provide enough structure and variation
to exercise the analytics and investigation architecture.

------------------------------------------------------------------------

# 18. Data Model and Investigation Mapping

The investigation catalog maps naturally to the data model.

  Investigation area     Primary data
  ---------------------- -------------------------------------
  Revenue trend          `sales`
  Regional performance   `sales` + `stores`
  Product performance    `sales` + `products`
  Category performance   `sales` + `products`
  Customer segments      `sales` + `customers`
  Promotion impact       `sales` + `products` + `promotions`
  Inventory stockouts    `inventory` + `products` + `stores`

This mapping allows investigation planning to select evidence domains
without giving the LLM unrestricted database access.

------------------------------------------------------------------------

# 19. Data Model Summary

The Nexa data model follows a simple analytical structure:

``` text
                  Customers
                      │
                      │
                      ▼
Products ────────► Sales ◄──────── Stores
   │
   ├────────────► Promotions
   │
   └────────────► Inventory ◄──── Stores
```

`Sales` acts as the central transactional fact source, while
`customers`, `products`, and `stores` provide business dimensions.

`promotions` and `inventory` provide additional operational context used
by the investigation workflows.

The model is intentionally simple enough for local development while
being rich enough to demonstrate:

-   Conversational analytics
-   Multi-dimensional analysis
-   Investigation planning
-   Evidence collection
-   Anomaly detection
-   Business reasoning
-   Controlled LLM-to-data integration
