"""
SecureBank Connect - SQLite Database & Seed Data
Aligned with Official ER Diagram (7 Core Tables + Compatibility Views & Triggers)
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
    """Initializes tables matching the ER diagram and seeds synthetic demo data."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Developers Table (ER Diagram Table 1)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS developers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        developer_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        company_name TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        status TEXT DEFAULT 'ACTIVE',
        created_at TEXT NOT NULL
    );
    """)

    # 2. Users / Bank Customers Table (ER Diagram Table 2)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE NOT NULL,
        customer_id TEXT,
        name TEXT NOT NULL,
        full_name TEXT,
        email TEXT NOT NULL,
        phone_number TEXT NOT NULL,
        phone TEXT,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'CUSTOMER',
        kyc_status TEXT DEFAULT 'VERIFIED',
        created_at TEXT NOT NULL
    );
    """)

    # 3. Applications / Partner Apps Table (ER Diagram Table 3)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        app_id TEXT UNIQUE NOT NULL,
        developer_id TEXT NOT NULL,
        app_name TEXT NOT NULL,
        name TEXT,
        description TEXT,
        redirect_url TEXT,
        client_id TEXT UNIQUE NOT NULL,
        client_secret TEXT NOT NULL,
        api_key TEXT UNIQUE NOT NULL,
        allowed_scopes TEXT NOT NULL,
        rate_limit INTEGER DEFAULT 60,
        status TEXT DEFAULT 'ACTIVE',
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        FOREIGN KEY (developer_id) REFERENCES developers(developer_id)
    );
    """)

    # 4. Bank Accounts Table (ER Diagram Table 4)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id TEXT UNIQUE NOT NULL,
        user_id TEXT NOT NULL,
        customer_id TEXT,
        account_number TEXT UNIQUE NOT NULL,
        account_type TEXT NOT NULL,
        bank_name TEXT NOT NULL DEFAULT 'SecureBank Digital',
        currency TEXT DEFAULT 'USD',
        balance REAL NOT NULL,
        available_balance REAL NOT NULL,
        status TEXT DEFAULT 'ACTIVE',
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """)

    # 5. Bank Transactions Table (ER Diagram Table 5)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id TEXT UNIQUE NOT NULL,
        account_id TEXT NOT NULL,
        date TEXT NOT NULL,
        timestamp TEXT,
        type TEXT NOT NULL, -- 'DEBIT' or 'CREDIT'
        amount REAL NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        status TEXT DEFAULT 'SETTLED',
        reference_id TEXT NOT NULL,
        reference TEXT,
        counterparty TEXT,
        FOREIGN KEY (account_id) REFERENCES accounts(account_id)
    );
    """)

    # 6. Customer Consents Table (ER Diagram Table 6)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS consents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        consent_id TEXT UNIQUE NOT NULL,
        user_id TEXT NOT NULL,
        customer_id TEXT,
        app_id TEXT NOT NULL,
        account_id TEXT,
        scopes TEXT NOT NULL,
        status TEXT NOT NULL, -- 'ACTIVE', 'REVOKED', 'EXPIRED'
        granted_at TEXT NOT NULL,
        created_at TEXT,
        expires_at TEXT NOT NULL,
        revoked_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (app_id) REFERENCES applications(client_id)
    );
    """)

    # 7. API Logs Table (ER Diagram Table 7)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_id INTEGER,
        app_id TEXT,
        endpoint TEXT NOT NULL,
        method TEXT NOT NULL,
        request_payload TEXT,
        response_status INTEGER NOT NULL,
        status_code INTEGER,
        response_time REAL NOT NULL,
        response_time_ms REAL,
        ip_address TEXT NOT NULL,
        payload_size INTEGER DEFAULT 0,
        is_anomalous INTEGER DEFAULT 0,
        anomaly_score REAL DEFAULT 0.0,
        created_at TEXT NOT NULL,
        timestamp TEXT
    );
    """)

    # 8. AI Alerts Table (ER Diagram Table 8)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_id TEXT UNIQUE NOT NULL,
        log_id INTEGER,
        app_id TEXT NOT NULL,
        alert_type TEXT NOT NULL,
        severity TEXT NOT NULL, -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
        description TEXT NOT NULL,
        status TEXT DEFAULT 'ACTIVE', -- 'ACTIVE', 'ACKNOWLEDGED', 'RESOLVED'
        ai_confidence REAL NOT NULL,
        created_at TEXT NOT NULL,
        timestamp TEXT
    );
    """)

    # Backward-compatibility views
    cursor.execute("CREATE VIEW IF NOT EXISTS partner_apps AS SELECT * FROM applications;")
    cursor.execute("CREATE VIEW IF NOT EXISTS bank_customers AS SELECT * FROM users;")
    cursor.execute("CREATE VIEW IF NOT EXISTS bank_accounts AS SELECT * FROM accounts;")
    cursor.execute("CREATE VIEW IF NOT EXISTS bank_transactions AS SELECT * FROM transactions;")
    cursor.execute("CREATE VIEW IF NOT EXISTS audit_logs AS SELECT * FROM api_logs;")
    cursor.execute("CREATE VIEW IF NOT EXISTS security_alerts AS SELECT * FROM alerts;")

    # INSTEAD OF triggers for seamless read/write on compatibility views
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS trig_audit_logs_insert INSTEAD OF INSERT ON audit_logs
    BEGIN
        INSERT INTO api_logs (app_id, endpoint, method, response_status, status_code, response_time, response_time_ms, ip_address, payload_size, is_anomalous, anomaly_score, created_at, timestamp)
        VALUES (NEW.app_id, NEW.endpoint, NEW.method, NEW.status_code, NEW.status_code, NEW.response_time_ms, NEW.response_time_ms, NEW.ip_address, NEW.payload_size, NEW.is_anomalous, NEW.anomaly_score, NEW.timestamp, NEW.timestamp);
    END;
    """)

    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS trig_bank_accounts_update INSTEAD OF UPDATE ON bank_accounts
    BEGIN
        UPDATE accounts SET balance = NEW.balance, available_balance = NEW.available_balance WHERE account_id = NEW.account_id;
    END;
    """)

    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS trig_bank_tx_insert INSTEAD OF INSERT ON bank_transactions
    BEGIN
        INSERT INTO transactions (transaction_id, account_id, date, timestamp, type, amount, description, category, status, reference_id, reference, counterparty)
        VALUES (NEW.transaction_id, NEW.account_id, NEW.timestamp, NEW.timestamp, NEW.type, NEW.amount, NEW.description, NEW.category, 'SETTLED', NEW.reference, NEW.reference, NEW.counterparty);
    END;
    """)

    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS trig_sec_alerts_insert INSTEAD OF INSERT ON security_alerts
    BEGIN
        INSERT INTO alerts (alert_id, app_id, alert_type, severity, description, status, ai_confidence, created_at, timestamp)
        VALUES (NEW.alert_id, NEW.app_id, NEW.alert_type, NEW.severity, NEW.description, NEW.status, NEW.ai_confidence, NEW.timestamp, NEW.timestamp);
    END;
    """)

    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS trig_partner_apps_insert INSTEAD OF INSERT ON partner_apps
    BEGIN
        INSERT INTO applications (app_id, developer_id, app_name, name, description, redirect_url, client_id, client_secret, api_key, allowed_scopes, rate_limit, status, is_active, created_at)
        VALUES (NEW.client_id, 'DEV-101', NEW.name, NEW.name, '', '', NEW.client_id, NEW.client_secret, NEW.api_key, NEW.allowed_scopes, NEW.rate_limit, 'ACTIVE', NEW.is_active, NEW.created_at);
    END;
    """)

    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS trig_partner_apps_update INSTEAD OF UPDATE ON partner_apps
    BEGIN
        UPDATE applications SET is_active = NEW.is_active, status = CASE WHEN NEW.is_active = 1 THEN 'ACTIVE' ELSE 'SUSPENDED' END WHERE client_id = NEW.client_id;
    END;
    """)

    conn.commit()

    # Seed data if applications table is empty
    cursor.execute("SELECT COUNT(*) AS count FROM applications")
    if cursor.fetchone()["count"] == 0:
        seed_synthetic_data(conn)

    conn.close()

def seed_synthetic_data(conn):
    """Populates realistic synthetic open-banking records matching the ER diagram."""
    cursor = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc)
    now_str = now.isoformat()

    # 1. Seed Developers
    developers = [
        ("DEV-101", "Alex Chen", "alex.chen@finpulse.io", "FinPulse Technologies Inc.", "hash_scrypt_9a8f", "ACTIVE", now_str),
        ("DEV-102", "Elena Rostova", "elena@quickinvoice.pro", "QuickInvoice Software Group", "hash_scrypt_3b2a", "ACTIVE", now_str),
        ("DEV-103", "Marcus Vance", "marcus@wealthtrack.ai", "WealthTrack Analytics Corp", "hash_scrypt_7e8d", "ACTIVE", now_str),
    ]
    cursor.executemany("""
    INSERT INTO developers (developer_id, name, email, company_name, password_hash, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, developers)

    # 2. Seed Users (Customers)
    users = [
        ("CUST-1001", "CUST-1001", "Sarah Jenkins", "Sarah Jenkins", "sarah.jenkins@example.com", "+1-415-555-0192", "+1-415-555-0192", "hash_pwd_01", "CUSTOMER", "VERIFIED", now_str),
        ("CUST-1002", "CUST-1002", "Priya Sharma", "Priya Sharma", "priya.sharma@example.com", "+1-415-555-0144", "+1-415-555-0144", "hash_pwd_02", "CUSTOMER", "VERIFIED", now_str),
        ("CUST-1003", "CUST-1003", "Alex Rivera", "Alex Rivera", "alex.rivera@example.com", "+1-415-555-0188", "+1-415-555-0188", "hash_pwd_03", "CUSTOMER", "VERIFIED", now_str),
    ]
    cursor.executemany("""
    INSERT INTO users (user_id, customer_id, name, full_name, email, phone_number, phone, password_hash, role, kyc_status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, users)

    # 3. Seed Applications (Partner Apps)
    apps = [
        (
            "APP-FINPULSE", "DEV-101", "FinPulse Smart Budgeting", "FinPulse Smart Budgeting",
            "AI-powered budgeting & expense insights", "https://finpulse.io/callback",
            "app_finpulse_9281", "sec_live_9a8f7c6e5d4b", "sb_live_finpulse_k9281a",
            json.dumps(["accounts:read", "balances:read", "transactions:read"]),
            60, "ACTIVE", 1, now_str
        ),
        (
            "APP-QUICKINV", "DEV-102", "QuickInvoice Pro", "QuickInvoice Pro",
            "Automated invoicing & synthetic vendor payment settlements", "https://quickinvoice.pro/oauth",
            "app_quickinv_4412", "sec_live_3b2a1c9e8f7d", "sb_live_quickinv_m4412x",
            json.dumps(["accounts:read", "balances:read", "payments:create"]),
            60, "ACTIVE", 1, now_str
        ),
        (
            "APP-WEALTHTRACK", "DEV-103", "WealthTrack AI Analytics", "WealthTrack AI Analytics",
            "Portfolio tracking & open banking analytics", "https://wealthtrack.ai/auth",
            "app_wealth_7730", "sec_live_7e8d9c0a1b2c", "sb_live_wealth_p7730q",
            json.dumps(["accounts:read", "balances:read", "transactions:read"]),
            90, "ACTIVE", 1, now_str
        ),
    ]
    cursor.executemany("""
    INSERT INTO applications (app_id, developer_id, app_name, name, description, redirect_url, client_id, client_secret, api_key, allowed_scopes, rate_limit, status, is_active, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, apps)

    # 4. Seed Accounts
    accounts = [
        ("ACC-US-8901", "CUST-1001", "CUST-1001", "40928192801", "CHECKING", "SecureBank Digital Trust", "USD", 14850.50, 14250.50, "ACTIVE", now_str),
        ("ACC-US-8902", "CUST-1001", "CUST-1001", "40928192802", "SAVINGS", "SecureBank Digital Trust", "USD", 54300.00, 54300.00, "ACTIVE", now_str),
        ("ACC-US-8903", "CUST-1002", "CUST-1002", "50192837401", "BUSINESS_OPERATING", "SecureBank Commercial", "USD", 128450.75, 126900.00, "ACTIVE", now_str),
        ("ACC-US-8904", "CUST-1002", "CUST-1002", "50192837402", "SAVINGS_RESERVE", "SecureBank Commercial", "USD", 85000.00, 85000.00, "ACTIVE", now_str),
        ("ACC-US-8905", "CUST-1003", "CUST-1003", "60293847101", "CHECKING", "SecureBank Community", "USD", 6200.20, 5950.00, "ACTIVE", now_str),
    ]
    cursor.executemany("""
    INSERT INTO accounts (account_id, user_id, customer_id, account_number, account_type, bank_name, currency, balance, available_balance, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, accounts)

    # 5. Seed Transactions
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
        INSERT INTO transactions (transaction_id, account_id, date, timestamp, type, amount, description, category, status, reference_id, reference, counterparty)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'SETTLED', ?, ?, ?)
        """, (tx_id, tx[0], dt, dt, tx[4], tx[3], tx[1], tx[2], tx[6], tx[6], tx[5]))

    # 6. Seed Consents
    consents = [
        (
            "CNS-9011-SARAH",
            "CUST-1001",
            "CUST-1001",
            "app_finpulse_9281",
            "ACC-US-8901",
            json.dumps(["accounts:read", "balances:read", "transactions:read"]),
            "ACTIVE",
            now_str,
            now_str,
            (now + datetime.timedelta(days=90)).isoformat(),
            None
        ),
        (
            "CNS-9012-PRIYA",
            "CUST-1002",
            "CUST-1002",
            "app_quickinv_4412",
            "ACC-US-8903",
            json.dumps(["accounts:read", "balances:read", "payments:create"]),
            "ACTIVE",
            now_str,
            now_str,
            (now + datetime.timedelta(days=180)).isoformat(),
            None
        ),
        (
            "CNS-9013-ALEX",
            "CUST-1003",
            "CUST-1003",
            "app_wealth_7730",
            "ACC-US-8905",
            json.dumps(["accounts:read", "balances:read"]),
            "REVOKED",
            (now - datetime.timedelta(days=10)).isoformat(),
            (now - datetime.timedelta(days=10)).isoformat(),
            (now + datetime.timedelta(days=30)).isoformat(),
            (now - datetime.timedelta(days=2)).isoformat()
        ),
    ]
    cursor.executemany("""
    INSERT INTO consents (consent_id, user_id, customer_id, app_id, account_id, scopes, status, granted_at, created_at, expires_at, revoked_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, consents)

    # 7. Seed Initial API Logs
    for i in range(50):
        t = (now - datetime.timedelta(minutes=random.randint(1, 120))).isoformat()
        app = random.choice(["app_finpulse_9281", "app_quickinv_4412", "app_wealth_7730"])
        endpoint = random.choice(["/api/v1/accounts", "/api/v1/accounts/ACC-US-8901/balances", "/api/v1/accounts/ACC-US-8901/transactions"])
        status = 200 if random.random() > 0.05 else random.choice([401, 403, 404])
        latency = round(random.uniform(25.0, 110.0), 2)
        payload_sz = random.randint(300, 1500)
        score = round(random.uniform(0.01, 0.15), 3)

        cursor.execute("""
        INSERT INTO api_logs (app_id, endpoint, method, request_payload, response_status, status_code, response_time, response_time_ms, ip_address, payload_size, is_anomalous, anomaly_score, created_at, timestamp)
        VALUES (?, ?, 'GET', '', ?, ?, ?, ?, '192.168.1.10', ?, 0, ?, ?, ?)
        """, (app, endpoint, status, status, latency, latency, payload_sz, score, t, t))

    # 8. Seed Initial Alert
    cursor.execute("""
    INSERT INTO alerts (alert_id, log_id, app_id, alert_type, severity, description, status, ai_confidence, created_at, timestamp)
    VALUES (?, 1, ?, 'REVOKED_CONSENT_PROBE', 'MEDIUM', 'App attempted 4 requests against customer ACC-US-8905 whose consent was revoked.', 'ACTIVE', 0.89, ?, ?)
    """, ("ALT-AI-8812", "app_wealth_7730", now_str, now_str))

    conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database aligned with ER diagram successfully.")
