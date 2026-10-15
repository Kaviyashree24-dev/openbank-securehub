"""
SecureBank Connect - Mock Banking Services & Synthetic Ledger
"""
import uuid
import datetime
from server.database import get_db_connection

def get_accounts_by_customer(customer_id: str):
    """Retrieves all bank accounts belonging to customer."""
    conn = get_db_connection()
    rows = conn.execute("""
    SELECT account_id, customer_id, account_number, account_type, currency, balance, available_balance, status
    FROM bank_accounts
    WHERE customer_id = ? AND status = 'ACTIVE'
    """, (customer_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_account_by_id(account_id: str):
    """Retrieves account details by account ID."""
    conn = get_db_connection()
    row = conn.execute("""
    SELECT a.*, c.full_name AS customer_name, c.email AS customer_email
    FROM bank_accounts a
    JOIN bank_customers c ON a.customer_id = c.customer_id
    WHERE a.account_id = ?
    """, (account_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_account_balances(account_id: str):
    """Retrieves balance breakdown for an account."""
    acc = get_account_by_id(account_id)
    if not acc:
        return None
    return {
        "account_id": acc["account_id"],
        "account_number": acc["account_number"],
        "currency": acc["currency"],
        "current_balance": round(acc["balance"], 2),
        "available_balance": round(acc["available_balance"], 2),
        "as_of_date": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

def get_transactions_by_account(account_id: str, limit: int = 50, category: str = None):
    """Retrieves synthetic transaction history for an account."""
    conn = get_db_connection()
    query = """
    SELECT transaction_id, account_id, description, category, amount, type, timestamp, counterparty, reference
    FROM bank_transactions
    WHERE account_id = ?
    """
    params = [account_id]
    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def execute_payment_transfer(from_account_id: str, to_account_id: str, amount: float, currency: str = "USD", reference: str = "Payment"):
    """
    Simulates a secure Open Banking payment initiation and settlement.
    Deducts balance from source account and logs transaction.
    """
    if amount <= 0:
        return False, {"error": "invalid_amount", "message": "Payment amount must be greater than 0", "status_code": 400}

    conn = get_db_connection()
    cursor = conn.cursor()

    source = cursor.execute("SELECT * FROM bank_accounts WHERE account_id = ?", (from_account_id,)).fetchone()
    if not source:
        conn.close()
        return False, {"error": "account_not_found", "message": f"Source account '{from_account_id}' does not exist", "status_code": 404}

    source = dict(source)
    if source["available_balance"] < amount:
        conn.close()
        return False, {
            "error": "insufficient_funds",
            "message": f"Available balance (${source['available_balance']:.2f}) is insufficient for payment of ${amount:.2f}",
            "status_code": 400
        }

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payment_id = f"PAY-{uuid.uuid4().hex[:10].upper()}"
    new_balance = source["balance"] - amount
    new_avail = source["available_balance"] - amount

    # Deduct from source account
    cursor.execute("""
    UPDATE bank_accounts
    SET balance = ?, available_balance = ?
    WHERE account_id = ?
    """, (new_balance, new_avail, from_account_id))

    # Record Debit Transaction
    cursor.execute("""
    INSERT INTO bank_transactions (transaction_id, account_id, description, category, amount, type, timestamp, counterparty, reference)
    VALUES (?, ?, ?, 'Transfer / Payment', ?, 'DEBIT', ?, ?, ?)
    """, (payment_id, from_account_id, f"OpenBanking Payment to {to_account_id}", amount, now_iso, to_account_id, reference))

    # If destination account is internal, credit it
    dest = cursor.execute("SELECT * FROM bank_accounts WHERE account_id = ?", (to_account_id,)).fetchone()
    if dest:
        dest_dict = dict(dest)
        cursor.execute("""
        UPDATE bank_accounts
        SET balance = balance + ?, available_balance = available_balance + ?
        WHERE account_id = ?
        """, (amount, amount, to_account_id))

        cursor.execute("""
        INSERT INTO bank_transactions (transaction_id, account_id, description, category, amount, type, timestamp, counterparty, reference)
        VALUES (?, ?, ?, 'Transfer / Payment', ?, 'CREDIT', ?, ?, ?)
        """, (f"{payment_id}-CR", to_account_id, f"Payment received from {from_account_id}", amount, now_iso, from_account_id, reference))

    conn.commit()
    conn.close()

    return True, {
        "payment_id": payment_id,
        "status": "SETTLED",
        "amount": amount,
        "currency": currency,
        "from_account_id": from_account_id,
        "to_account_id": to_account_id,
        "reference": reference,
        "settled_at": now_iso,
        "remaining_available_balance": round(new_avail, 2)
    }
