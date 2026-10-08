import random
from datetime import date, timedelta

from app.database.connection import get_connection


random.seed(42)


NUM_CUSTOMERS = 10_000
NUM_PRODUCTS = 100
NUM_STORES = 200
NUM_SALES = 250_000
NUM_PROMOTIONS = 300
SALES_START_DATE = date(2026, 1, 1)
SALES_END_DATE = date(2026, 9, 30)

STORE_TYPE_MULTIPLIER = {
    "Supermarket": 1.30,
    "Convenience": 0.80,
    "E-commerce": 1.15,
    "Distributor": 1.50,
}

REGION_MULTIPLIER = {
    "South": 1.15,
    "West": 1.20,
    "North": 1.00,
    "East": 0.90,
}

SEGMENT_MULTIPLIER = {
    "Premium": 1.60,
    "Standard": 1.00,
    "Value": 0.70,
}

STATES = {
    "Tamil Nadu": "South",
    "Karnataka": "South",
    "Kerala": "South",
    "Telangana": "South",
    "Maharashtra": "West",
    "Gujarat": "West",
    "Rajasthan": "North",
    "Delhi": "North",
    "Uttar Pradesh": "North",
    "West Bengal": "East",
}

CITIES = {
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Salem"],
    "Karnataka": ["Bengaluru", "Mysuru", "Mangaluru"],
    "Kerala": ["Kochi", "Thiruvananthapuram", "Kozhikode"],
    "Telangana": ["Hyderabad", "Warangal"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara"],
    "Rajasthan": ["Jaipur", "Udaipur", "Jodhpur"],
    "Delhi": ["New Delhi"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Agra"],
    "West Bengal": ["Kolkata", "Siliguri"],
}

PRODUCT_CATEGORIES = {
    "Personal Care": [
        "Shampoo",
        "Soap",
        "Face Wash",
        "Body Lotion",
        "Toothpaste",
    ],
    "Home Care": [
        "Laundry Detergent",
        "Dishwash",
        "Floor Cleaner",
        "Toilet Cleaner",
    ],
    "Food & Beverages": [
        "Biscuits",
        "Juice",
        "Breakfast Cereal",
        "Instant Noodles",
        "Energy Drink",
    ],
}

BRANDS = [
    "Nexa",
    "PureLife",
    "FreshDay",
    "UrbanChoice",
    "DailyPlus",
]

CUSTOMER_SEGMENTS = {
    "Premium": {
        "weight": 0.15,
        "spend_multiplier": 1.8,
    },
    "Standard": {
        "weight": 0.55,
        "spend_multiplier": 1.0,
    },
    "Value": {
        "weight": 0.30,
        "spend_multiplier": 0.65,
    },
}

def generate_customers(connection):
    rows = []

    states = list(STATES.keys())

    for customer_id in range(1, NUM_CUSTOMERS + 1):

        state = random.choice(states)
        city = random.choice(CITIES[state])

        segment = random.choices(
            list(CUSTOMER_SEGMENTS.keys()),
            weights=[
                CUSTOMER_SEGMENTS["Premium"]["weight"],
                CUSTOMER_SEGMENTS["Standard"]["weight"],
                CUSTOMER_SEGMENTS["Value"]["weight"],
            ],
        )[0]

        age_group = random.choices(
            ["18-24", "25-34", "35-44", "45-54", "55+"],
            weights=[0.12, 0.30, 0.28, 0.20, 0.10],
        )[0]

        gender = random.choice(["Male", "Female"])

        registration_date = date(
            random.randint(2022, 2026),
            random.randint(1, 12),
            random.randint(1, 28),
        )

        rows.append(
            (
                customer_id,
                f"Customer {customer_id}",
                gender,
                age_group,
                city,
                state,
                segment,
                registration_date.isoformat(),
            )
        )

    connection.executemany(
        """
        INSERT INTO customers (
            customer_id,
            customer_name,
            gender,
            age_group,
            city,
            state,
            customer_segment,
            registration_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    connection.commit()

    print(f"Generated {len(rows):,} customers.")

def generate_products(connection):
    rows = []

    product_id = 1

    for category, subcategories in PRODUCT_CATEGORIES.items():

        for _ in range(NUM_PRODUCTS // len(PRODUCT_CATEGORIES)):

            subcategory = random.choice(subcategories)
            brand = random.choice(BRANDS)

            unit_price = round(
                random.uniform(50, 800),
                2,
            )

            cost = round(
                unit_price * random.uniform(0.45, 0.70),
                2,
            )

            rows.append(
                (
                    product_id,
                    f"{brand} {subcategory} {product_id}",
                    category,
                    subcategory,
                    brand,
                    unit_price,
                    cost,
                )
            )

            product_id += 1

    connection.executemany(
        """
        INSERT INTO products (
            product_id,
            product_name,
            category,
            subcategory,
            brand,
            unit_price,
            cost
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    connection.commit()

    print(f"Generated {len(rows):,} products.")


STORE_TYPES = [
    "Supermarket",
    "Convenience",
    "E-commerce",
    "Distributor",
]

def generate_stores(connection):
    rows = []

    states = list(STATES.keys())

    for store_id in range(1, NUM_STORES + 1):

        state = random.choice(states)
        city = random.choice(CITIES[state])
        region = STATES[state]
        store_type = random.choice(STORE_TYPES)

        rows.append(
            (
                store_id,
                f"Store {store_id}",
                city,
                state,
                region,
                store_type,
            )
        )

    connection.executemany(
        """
        INSERT INTO stores (
            store_id,
            store_name,
            city,
            state,
            region,
            store_type
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    connection.commit()

    print(f"Generated {len(rows):,} stores.")

PROMOTION_TYPES = [
    "Discount",
    "Buy One Get One",
    "Bundle",
    "Seasonal",
]

def generate_promotions(connection):
    rows = []

    for promotion_id in range(1, NUM_PROMOTIONS + 1):

        product_id = random.randint(1, NUM_PRODUCTS)

        store_id = random.choice(
            [None] + list(range(1, NUM_STORES + 1))
        )

        start_date = date(
            2026,
            random.randint(1, 10),
            random.randint(1, 20),
        )

        duration = random.randint(7, 30)
        end_date = start_date + timedelta(days=duration)

        promotion_type = random.choice(PROMOTION_TYPES)

        discount_percentage = round(
            random.uniform(5, 30),
            2,
        )

        rows.append(
            (
                promotion_id,
                product_id,
                store_id,
                promotion_type,
                start_date.isoformat(),
                end_date.isoformat(),
                discount_percentage,
            )
        )

    connection.executemany(
        """
        INSERT INTO promotions (
            promotion_id,
            product_id,
            store_id,
            promotion_type,
            start_date,
            end_date,
            discount_percentage
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    connection.commit()

    print(f"Generated {len(rows):,} promotions.")

def generate_inventory(connection):
    rows = []

    inventory_id = 1

    start_date = date(2026, 1, 1)

    for _ in range(100_000):

        product_id = random.randint(1, NUM_PRODUCTS)
        store_id = random.randint(1, NUM_STORES)

        inventory_date = start_date + timedelta(
            days=random.randint(0, 270)
        )

        opening_stock = random.randint(20, 500)

        stockout = random.random() < 0.05

        if stockout:
            closing_stock = 0
            stockout_flag = 1
        else:
            closing_stock = random.randint(
                1,
                opening_stock,
            )
            stockout_flag = 0

        rows.append(
            (
                inventory_id,
                product_id,
                store_id,
                inventory_date.isoformat(),
                opening_stock,
                closing_stock,
                stockout_flag,
            )
        )

        inventory_id += 1

    connection.executemany(
        """
        INSERT INTO inventory (
            inventory_id,
            product_id,
            store_id,
            inventory_date,
            opening_stock,
            closing_stock,
            stockout_flag
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    connection.commit()

    print(f"Generated {len(rows):,} inventory records.")

def random_date(start_date, end_date):
    days = (end_date - start_date).days

    return start_date + timedelta(
        days=random.randint(0, days)
    )

def load_reference_data(connection):

    customers = connection.execute("""
        SELECT
            customer_id,
            customer_segment
        FROM customers
    """).fetchall()

    products = connection.execute("""
        SELECT
            product_id,
            unit_price,
            cost,
            category
        FROM products
    """).fetchall()

    stores = connection.execute("""
        SELECT
            store_id,
            region,
            store_type
        FROM stores
    """).fetchall()

    promotions = connection.execute("""
        SELECT
            promotion_id,
            product_id,
            store_id,
            start_date,
            end_date,
            discount_percentage
        FROM promotions
    """).fetchall()

    return customers, products, stores, promotions

def get_active_promotion(
    product_id,
    store_id,
    transaction_date,
    promotions,
):
    active_promotions = []

    for promotion in promotions:

        if promotion["product_id"] != product_id:
            continue

        if promotion["store_id"] is not None:
            if promotion["store_id"] != store_id:
                continue

        start_date = date.fromisoformat(
            promotion["start_date"]
        )

        end_date = date.fromisoformat(
            promotion["end_date"]
        )

        if start_date <= transaction_date <= end_date:
            active_promotions.append(promotion)

    if not active_promotions:
        return None

    return random.choice(active_promotions)

def generate_sales(connection):

    customers, products, stores, promotions = load_reference_data(
        connection
    )

    rows = []

    transaction_id = 1

    for _ in range(NUM_SALES):

        customer = random.choice(customers)
        product = random.choice(products)
        store = random.choice(stores)

        transaction_date = random_date(
            SALES_START_DATE,
            SALES_END_DATE,
        )

        customer_multiplier = SEGMENT_MULTIPLIER[
            customer["customer_segment"]
        ]

        store_multiplier = STORE_TYPE_MULTIPLIER[
            store["store_type"]
        ]

        region_multiplier = REGION_MULTIPLIER[
            store["region"]
        ]

        product_multiplier = random.uniform(
            0.6,
            1.8,
        )

        base_probability = (
            customer_multiplier
            * store_multiplier
            * region_multiplier
            * product_multiplier
        )

        quantity = max(
            1,
            int(
                random.gauss(
                    2 * base_probability,
                    1.2,
                )
            ),
        )

        promotion = get_active_promotion(
            product["product_id"],
            store["store_id"],
            transaction_date,
            promotions,
        )

        discount = 0

        if promotion:
            discount = promotion["discount_percentage"]

            promotion_boost = random.uniform(
                1.10,
                1.60,
            )

            quantity = max(
                quantity,
                int(quantity * promotion_boost),
            )

        unit_price = product["unit_price"]

        sales_amount = (
            quantity
            * unit_price
            * (1 - discount / 100)
        )

        rows.append(
            (
                transaction_id,
                transaction_date.isoformat(),
                customer["customer_id"],
                product["product_id"],
                store["store_id"],
                quantity,
                unit_price,
                discount,
                round(sales_amount, 2),
            )
        )

        transaction_id += 1

        if len(rows) >= 5000:
            connection.executemany(
                """
                INSERT INTO sales (
                    transaction_id,
                    transaction_date,
                    customer_id,
                    product_id,
                    store_id,
                    quantity,
                    unit_price,
                    discount,
                    sales_amount
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

            connection.commit()

            rows.clear()

            print(
                f"Generated {transaction_id - 1:,} sales..."
            )

    if rows:
        connection.executemany(
            """
            INSERT INTO sales (
                transaction_id,
                transaction_date,
                customer_id,
                product_id,
                store_id,
                quantity,
                unit_price,
                discount,
                sales_amount
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

        connection.commit()

    print(f"Generated {transaction_id - 1:,} sales.")


def main():
    connection = get_connection()

    try:
        generate_customers(connection)
        generate_products(connection)
        generate_stores(connection)
        generate_promotions(connection)
        generate_inventory(connection)
        generate_sales(connection)

    finally:
        connection.close()


if __name__ == "__main__":
    main()