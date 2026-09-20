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
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    brand TEXT NOT NULL,
    unit_price REAL NOT NULL,
    cost REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS stores (
    store_id INTEGER PRIMARY KEY,
    store_name TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    region TEXT NOT NULL,
    store_type TEXT NOT NULL
);
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

    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id),

    FOREIGN KEY (product_id)
        REFERENCES products(product_id),

    FOREIGN KEY (store_id)
        REFERENCES stores(store_id)
);
CREATE TABLE IF NOT EXISTS promotions (
    promotion_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    store_id INTEGER,
    promotion_type TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    discount_percentage REAL NOT NULL,

    FOREIGN KEY (product_id)
        REFERENCES products(product_id),

    FOREIGN KEY (store_id)
        REFERENCES stores(store_id)
);
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    store_id INTEGER NOT NULL,
    inventory_date DATE NOT NULL,
    opening_stock INTEGER NOT NULL,
    closing_stock INTEGER NOT NULL,
    stockout_flag INTEGER DEFAULT 0,

    FOREIGN KEY (product_id)
        REFERENCES products(product_id),

    FOREIGN KEY (store_id)
        REFERENCES stores(store_id)
);
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
