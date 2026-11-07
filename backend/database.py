import sqlite3
import os
import math

DB_PATH = os.path.join(os.path.dirname(__file__), "telecom.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees)
    """
    R = 6371.0 # Radius of the earth in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. telecom_operators
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS telecom_operators (
        operator_id INTEGER PRIMARY KEY AUTOINCREMENT,
        operator_name TEXT NOT NULL UNIQUE,
        logo TEXT NOT NULL,
        brand_color TEXT NOT NULL,
        website TEXT,
        support_number TEXT,
        status TEXT DEFAULT 'Active'
    );
    """)

    # 2. locations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS locations (
        location_id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT NOT NULL,
        district TEXT NOT NULL,
        state TEXT NOT NULL,
        pincode TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL
    );
    """)

    # 3. plans
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS plans (
        plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        operator_id INTEGER NOT NULL,
        plan_name TEXT NOT NULL,
        price REAL NOT NULL,
        validity TEXT NOT NULL,
        daily_data TEXT NOT NULL,
        total_data TEXT,
        voice TEXT DEFAULT 'Unlimited',
        sms TEXT DEFAULT '100 SMS/day',
        ott_benefit TEXT,
        status TEXT DEFAULT 'Active',
        FOREIGN KEY (operator_id) REFERENCES telecom_operators (operator_id) ON DELETE CASCADE
    );
    """)

    # 4. customers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        mobile_number TEXT NOT NULL UNIQUE,
        email TEXT,
        operator_id INTEGER NOT NULL,
        plan_id INTEGER NOT NULL,
        city TEXT NOT NULL,
        district TEXT NOT NULL,
        state TEXT NOT NULL,
        pincode TEXT NOT NULL,
        latitude REAL,
        longitude REAL,
        validity_days_remaining INTEGER DEFAULT 28,
        data_remaining TEXT DEFAULT '1.5 GB / 2.0 GB left today',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (operator_id) REFERENCES telecom_operators (operator_id) ON DELETE CASCADE,
        FOREIGN KEY (plan_id) REFERENCES plans (plan_id) ON DELETE CASCADE
    );
    """)

    # 5. diwali_offers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS diwali_offers (
        offer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        operator_id INTEGER NOT NULL,
        location_id INTEGER,
        offer_name TEXT NOT NULL,
        price REAL NOT NULL,
        validity TEXT NOT NULL,
        data TEXT NOT NULL,
        voice TEXT DEFAULT 'Unlimited Calls',
        sms TEXT DEFAULT '100 SMS/day',
        bonus TEXT,
        discount TEXT,
        start_date TEXT DEFAULT '2026-10-15',
        end_date TEXT DEFAULT '2026-11-20',
        badge TEXT DEFAULT 'DIWALI SPECIAL',
        status TEXT DEFAULT 'Active',
        FOREIGN KEY (operator_id) REFERENCES telecom_operators (operator_id) ON DELETE CASCADE,
        FOREIGN KEY (location_id) REFERENCES locations (location_id) ON DELETE SET NULL
    );
    """)

    # 6. transactions (recharge / offer claim records)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recharge_transactions (
        transaction_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        mobile_number TEXT NOT NULL,
        offer_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        payment_method TEXT DEFAULT 'UPI',
        status TEXT DEFAULT 'Success',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
        FOREIGN KEY (offer_id) REFERENCES diwali_offers (offer_id)
    );
    """)

    # 7. user_locations (Stores exact 'Turn on Location' event in database)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_locations (
        location_log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        mobile_number TEXT,
        customer_id TEXT,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        accuracy_meters REAL,
        exact_address TEXT,
        locality TEXT,
        resolved_city TEXT,
        resolved_district TEXT,
        resolved_state TEXT,
        resolved_pincode TEXT,
        distance_km REAL,
        status TEXT DEFAULT 'Granted',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Safe schema migration for exact location fields
    for col_name, col_type in [("exact_address", "TEXT"), ("locality", "TEXT"), ("accuracy_meters", "REAL"),
                                ("google_maps_link", "TEXT"), ("visitor_name", "TEXT"), ("sim_type", "TEXT")]:
        try:
            cursor.execute(f"ALTER TABLE user_locations ADD COLUMN {col_name} {col_type};")
        except sqlite3.OperationalError:
            pass

    for col_name, col_type in [("exact_address", "TEXT"), ("locality", "TEXT"), ("google_maps_link", "TEXT")]:
        try:
            cursor.execute(f"ALTER TABLE customers ADD COLUMN {col_name} {col_type};")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database tables initialized successfully.")
