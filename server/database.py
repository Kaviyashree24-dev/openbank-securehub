"""
SecureBank Connect - SQLite Database & Seed Data
"""
import sqlite3
import json
import uuid
import datetime
import random
from server.config import DB_PATH

def get_db_connection():
    """Returns a connection to the SQLite database with dictionary cursor."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    """Initializes tables and seeds synthetic demo data if empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Partner Apps Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS partner_apps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        client_id TEXT UNIQUE NOT NULL,
        client_secret TEXT NOT NULL,
        api_key TEXT UNIQUE NOT NULL,
        allowed_scopes TEXT NOT NULL,
        rate_limit INTEGER DEFAULT 60,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    );
    """)

    # 2. Bank Customers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bank_customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        kyc_status TEXT DEFAULT 'VERIFIED'
    );
    """)

    # 3. Bank Accounts Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bank_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id TEXT UNIQUE NOT NULL,
        customer_id TEXT NOT NULL,
        account_number TEXT UNIQUE NOT NULL,
        account_type TEXT NOT NULL,
        currency TEXT DEFAULT 'USD',
        balance REAL NOT NULL,
        available_balance REAL NOT NULL,
        status TEXT DEFAULT 'ACTIVE',
        FOREIGN KEY (customer_id) REFERENCES bank_customers(customer_id)
    );
    """)

    # 4. Bank Transactions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bank_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id TEXT UNIQUE NOT NULL,
        account_id TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        amount REAL NOT NULL,
        type TEXT NOT NULL, -- 'DEBIT' or 'CREDIT'
        timestamp TEXT NOT NULL,
        counterparty TEXT NOT NULL,
        reference TEXT NOT NULL,
        FOREIGN KEY (account_id) REFERENCES bank_accounts(account_id)
    );
    """)

    # 5. Customer Consents Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS consents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        consent_id TEXT UNIQUE NOT NULL,
        customer_id TEXT NOT NULL,
        app_id TEXT NOT NULL,
        scopes TEXT NOT NULL,
        status TEXT NOT NULL, -- 'ACTIVE', 'REVOKED', 'EXPIRED'
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        revoked_at TEXT,
        FOREIGN KEY (customer_id) REFERENCES bank_customers(customer_id),
        FOREIGN KEY (app_id) REFERENCES partner_apps(client_id)
    );
    """)

    # 6. Audit & Request Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        app_id TEXT,
        method TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        status_code INTEGER NOT NULL,
        ip_address TEXT NOT NULL,
        response_time_ms REAL NOT NULL,
        payload_size INTEGER DEFAULT 0,
        is_anomalous INTEGER DEFAULT 0,
        anomaly_score REAL DEFAULT 0.0
    );
    """)

    # 7. AI Security Alerts Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS security_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_id TEXT UNIQUE NOT NULL,
        timestamp TEXT NOT NULL,
        app_id TEXT NOT NULL,
        alert_type TEXT NOT NULL,
        severity TEXT NOT NULL, -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
        description TEXT NOT NULL,
        status TEXT DEFAULT 'ACTIVE', -- 'ACTIVE', 'ACKNOWLEDGED', 'RESOLVED'
        ai_confidence REAL NOT NULL
    );
    """)

    conn.commit()

    # Seed data if partner_apps is empty
    cursor.execute("SELECT COUNT(*) AS count FROM partner_apps")
    if cursor.fetchone()["count"] == 0:
        seed_synthetic_data(conn)

    conn.close()

def seed_synthetic_data(conn):
    """Populates realistic synthetic open-banking records."""
    cursor = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc)
    now_str = now.isoformat()

    # Seed Partner Apps
    apps = [
        ("FinPulse Smart Budgeting", "app_finpulse_9281", "sec_live_9a8f7c6e5d4b", "sb_live_finpulse_k9281a", json.dumps(["accounts:read", "balances:read", "transactions:read"]), 60, 1, now_str),
        ("QuickInvoice Pro", "app_quickinv_4412", "sec_live_3b2a1c9e8f7d", "sb_live_quickinv_m4412x", json.dumps(["accounts:read", "balances:read", "payments:create"]), 60, 1, now_str),
        ("WealthTrack AI Analytics", "app_wealth_7730", "sec_live_7e8d9c0a1b2c", "sb_live_wealth_p7730q", json.dumps(["accounts:read", "balances:read", "transactions:read"]), 90, 1, now_str),
    ]
    cursor.executemany("""
    INSERT INTO partner_apps (name, client_id, client_secret, api_key, allowed_scopes, rate_limit, is_active, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, apps)

    # Seed Customers
    customers = [
        ("CUST-1001", "Sarah Jenkins", "sarah.jenkins@example.com", "+1-415-555-0192", "VERIFIED"),
        ("CUST-1002", "Priya Sharma", "priya.sharma@example.com", "+1-415-555-0144", "VERIFIED"),
        ("CUST-1003", "Alex Rivera", "alex.rivera@example.com", "+1-415-555-0188", "VERIFIED"),
    ]
    cursor.executemany("""
    INSERT INTO bank_customers (customer_id, full_name, email, phone, kyc_status)
    VALUES (?, ?, ?, ?, ?)
    """, customers)

    # Seed Bank Accounts
    accounts = [
        ("ACC-US-8901", "CUST-1001", "40928192801", "CHECKING", "USD", 14850.50, 14250.50, "ACTIVE"),
        ("ACC-US-8902", "CUST-1001", "40928192802", "SAVINGS", "USD", 54300.00, 54300.00, "ACTIVE"),
        ("ACC-US-8903", "CUST-1002", "50192837401", "BUSINESS_OPERATING", "USD", 128450.75, 126900.00, "ACTIVE"),
        ("ACC-US-8904", "CUST-1002", "50192837402", "SAVINGS_RESERVE", "USD", 85000.00, 85000.00, "ACTIVE"),
        ("ACC-US-8905", "CUST-1003", "60293847101", "CHECKING", "USD", 6200.20, 5950.00, "ACTIVE"),
    ]
    cursor.executemany("""
    INSERT INTO bank_accounts (account_id, customer_id, account_number, account_type, currency, balance, available_balance, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, accounts)

    # Seed Bank Transactions
    tx_templates = [
        ("ACC-US-8901", "Amazon Web Services Inc.", "Cloud Infrastructure", 342.50, "DEBIT", "Amazon AWS", "AWS-INV-9921"),
        ("ACC-US-8901", "Payroll Direct Deposit - TechCorp", "Salary", 4500.00, "CREDIT", "TechCorp Global", "DIR-DEP-8831"),
        ("ACC-US-8901", "Starbucks Coffee #2819", "Food & Dining", 14.85, "DEBIT", "Starbucks Corp", "POS-STB-0192"),
        ("ACC-US-8901", "Whole Foods Market", "Groceries", 142.30, "DEBIT", "Whole Foods", "WFM-92819"),
        ("ACC-US-8901", "Monthly Apartment Rent", "Housing", 2200.00, "DEBIT", "Oakridge Properties", "ACH-RNT-4401"),
        ("ACC-US-8901", "Uber Technologies Inc.", "Transportation", 38.40, "DEBIT", "Uber BV", "UBR-90123"),
        ("ACC-US-8902", "High-Yield Interest Payout", "Interest Income", 182.40, "CREDIT", "SecureBank Treasury", "INT-CR-1029"),
        ("ACC-US-8902", "Internal Transfer from Checking", "Transfer", 1000.00, "CREDIT", "Sarah Jenkins", "INT-TRF-001"),
        ("ACC-US-8903", "Client Retainer - Nexus Enterprise", "Revenue", 18500.00, "CREDIT", "Nexus Enterprise LLC", "INV-2026-891"),
        ("ACC-US-8903", "Google Cloud Suite", "Software / SaaS", 540.00, "DEBIT", "Google LLC", "GOOG-66321"),
        ("ACC-US-8903", "Stripe Merchant Payout", "Merchant Settlement", 9420.80, "CREDIT", "Stripe Inc", "STRIPE-PO-441"),
        ("ACC-US-8903", "Dell Technologies Workstations", "Hardware / Office", 3450.00, "DEBIT", "Dell Computers", "DELL-INV-881"),
        ("ACC-US-8905", "Spotify Premium Family", "Entertainment", 17.99, "DEBIT", "Spotify AB", "SPOT-99218"),
        ("ACC-US-8905", "Trader Joe's Market", "Groceries", 84.60, "DEBIT", "Trader Joe's", "TJ-77401"),
        ("ACC-US-8905", "Freelance Design Retainer", "Income", 2800.00, "CREDIT", "Studio K Media", "INV-1092")
    ]

    for idx, tx in enumerate(tx_templates):
        tx_id = f"TXN-2026-{1000 + idx}"
        dt = (now - datetime.timedelta(days=random.randint(1, 20), hours=random.randint(1, 12))).isoformat()
        cursor.execute("""
        INSERT INTO bank_transactions (transaction_id, account_id, description, category, amount, type, timestamp, counterparty, reference)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tx_id, tx[0], tx[1], tx[2], tx[3], tx[4], dt, tx[5], tx[6]))

    # Seed Customer Consents
    consents = [
        (
            "CNS-9011-SARAH",
            "CUST-1001",
            "app_finpulse_9281",
            json.dumps(["accounts:read", "balances:read", "transactions:read"]),
            "ACTIVE",
            (now + datetime.timedelta(days=90)).isoformat(),
            now_str,
            None
        ),
        (
            "CNS-9012-PRIYA",
            "CUST-1002",
            "app_quickinv_4412",
            json.dumps(["accounts:read", "balances:read", "payments:create"]),
            "ACTIVE",
            (now + datetime.timedelta(days=180)).isoformat(),
            now_str,
            None
        ),
        (
            "CNS-9013-ALEX",
            "CUST-1003",
            "app_wealth_7730",
            json.dumps(["accounts:read", "balances:read"]),
            "REVOKED",
            (now + datetime.timedelta(days=30)).isoformat(),
            (now - datetime.timedelta(days=10)).isoformat(),
            (now - datetime.timedelta(days=2)).isoformat()
        ),
    ]
    cursor.executemany("""
    INSERT INTO consents (consent_id, customer_id, app_id, scopes, status, expires_at, created_at, revoked_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, consents)

    # Seed baseline audit logs for dashboard visualization & AI training baseline
    for i in range(50):
        t = (now - datetime.timedelta(minutes=random.randint(1, 120))).isoformat()
        app = random.choice(["app_finpulse_9281", "app_quickinv_4412", "app_wealth_7730"])
        endpoint = random.choice(["/api/v1/accounts", "/api/v1/accounts/ACC-US-8901/balances", "/api/v1/accounts/ACC-US-8901/transactions"])
        status = 200 if random.random() > 0.05 else random.choice([401, 403, 404])
        cursor.execute("""
        INSERT INTO audit_logs (timestamp, app_id, method, endpoint, status_code, ip_address, response_time_ms, payload_size, is_anomalous, anomaly_score)
        VALUES (?, ?, 'GET', ?, ?, '192.168.1.10', ?, ?, 0, ?)
        """, (t, app, endpoint, status, round(random.uniform(25.0, 110.0), 2), random.randint(300, 1500), round(random.uniform(0.01, 0.15), 3)))

    # Seed sample security alert
    cursor.execute("""
    INSERT INTO security_alerts (alert_id, timestamp, app_id, alert_type, severity, description, status, ai_confidence)
    VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
    """, (
        "ALT-AI-8812",
        now_str,
        "app_wealth_7730",
        "REVOKED_CONSENT_PROBE",
        "MEDIUM",
        "App attempted 4 requests against customer ACC-US-8905 whose consent was revoked.",
        0.89
    ))

    conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
