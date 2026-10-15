"""
SecureBank Connect - Explicit Customer Consent Management
"""
import json
import datetime
import uuid
from server.database import get_db_connection

def validate_customer_consent(customer_id: str, app_id: str, required_scope: str):
    """
    Strictly verifies whether an active, valid, non-revoked consent exists
    from the customer for the requesting partner application and scope.
    """
    conn = get_db_connection()
    row = conn.execute("""
    SELECT * FROM consents
    WHERE customer_id = ? AND app_id = ?
    ORDER BY id DESC LIMIT 1
    """, (customer_id, app_id)).fetchone()
    conn.close()

    if not row:
        return False, {
            "error": "consent_missing",
            "message": f"Customer '{customer_id}' has not granted consent to application '{app_id}'",
            "status_code": 403
        }

    consent = dict(row)

    # Check revocation
    if consent["status"] == "REVOKED":
        return False, {
            "error": "consent_revoked",
            "message": f"Customer '{customer_id}' has revoked access for application '{app_id}' at {consent.get('revoked_at')}",
            "status_code": 403
        }

    # Check expiration
    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        expires_at = datetime.datetime.fromisoformat(consent["expires_at"])
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
        if now > expires_at:
            return False, {
                "error": "consent_expired",
                "message": f"Customer consent expired on {consent['expires_at']}. Re-authorization required.",
                "status_code": 403
            }
    except Exception:
        pass

    # Check scope inclusion in customer grant
    try:
        granted_scopes = json.loads(consent["scopes"])
    except Exception:
        granted_scopes = []

    if required_scope not in granted_scopes:
        return False, {
            "error": "consent_scope_denied",
            "message": f"Customer consented to '{','.join(granted_scopes)}', but requested action requires '{required_scope}'",
            "status_code": 403
        }

    return True, consent

def create_consent(customer_id: str, app_id: str, scopes: list, duration_days: int = 90):
    """Creates a new explicit customer consent record."""
    conn = get_db_connection()
    now = datetime.datetime.now(datetime.timezone.utc)
    expires_at = (now + datetime.timedelta(days=duration_days)).isoformat()
    consent_id = f"CNS-{uuid.uuid4().hex[:8].upper()}"

    conn.execute("""
    INSERT INTO consents (consent_id, customer_id, app_id, scopes, status, expires_at, created_at)
    VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?)
    """, (consent_id, customer_id, app_id, json.dumps(scopes), expires_at, now.isoformat()))
    conn.commit()

    row = conn.execute("SELECT * FROM consents WHERE consent_id = ?", (consent_id,)).fetchone()
    conn.close()
    return dict(row)

def revoke_consent(consent_id: str):
    """Explicitly revokes an existing customer consent."""
    conn = get_db_connection()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cursor = conn.execute("""
    UPDATE consents
    SET status = 'REVOKED', revoked_at = ?
    WHERE consent_id = ?
    """, (now, consent_id))
    conn.commit()
    updated = cursor.rowcount > 0

    row = None
    if updated:
        row = conn.execute("SELECT * FROM consents WHERE consent_id = ?", (consent_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def list_consents(customer_id: str = None):
    """Lists all customer consents along with partner app details."""
    conn = get_db_connection()
    if customer_id:
        rows = conn.execute("""
        SELECT c.*, a.name AS app_name, cust.full_name AS customer_name
        FROM consents c
        JOIN partner_apps a ON c.app_id = a.client_id
        JOIN bank_customers cust ON c.customer_id = cust.customer_id
        WHERE c.customer_id = ?
        ORDER BY c.id DESC
        """, (customer_id,)).fetchall()
    else:
        rows = conn.execute("""
        SELECT c.*, a.name AS app_name, cust.full_name AS customer_name
        FROM consents c
        JOIN partner_apps a ON c.app_id = a.client_id
        JOIN bank_customers cust ON c.customer_id = cust.customer_id
        ORDER BY c.id DESC
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
