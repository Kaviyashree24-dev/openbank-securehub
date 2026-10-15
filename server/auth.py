"""
SecureBank Connect - Authentication & Scoped Token Management
"""
import hmac
import hashlib
import base64
import json
import time
from server.config import SECRET_KEY, TOKEN_EXPIRY_SECONDS
from server.database import get_db_connection

def b64url_encode(data: bytes) -> str:
    """Base64 URL-safe encoding without padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def b64url_decode(data: str) -> bytes:
    """Base64 URL-safe decoding with auto padding."""
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)

def generate_signed_token(app_id: str, scopes: list, customer_id: str = "CUST-1001", expiry_seconds: int = TOKEN_EXPIRY_SECONDS) -> str:
    """
    Generates a secure cryptographically signed Bearer token with scope claims.
    """
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "iss": "SecureBank-Gateway",
        "sub": app_id,
        "customer_id": customer_id,
        "scopes": scopes,
        "iat": now,
        "exp": now + expiry_seconds,
        "jti": hashlib.sha256(f"{app_id}{now}{scopes}".encode()).hexdigest()[:16]
    }

    header_b64 = b64url_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = b64url_encode(json.dumps(payload).encode("utf-8"))

    signature_raw = hmac.new(
        SECRET_KEY.encode("utf-8"),
        f"{header_b64}.{payload_b64}".encode("utf-8"),
        hashlib.sha256
    ).digest()
    sig_b64 = b64url_encode(signature_raw)

    return f"{header_b64}.{payload_b64}.{sig_b64}"

def verify_token(token: str):
    """
    Verifies Bearer token integrity, expiration, and returns decoded payload.
    Returns (is_valid, payload_or_error_dict).
    """
    if not token:
        return False, {"error": "Missing token", "status_code": 401}

    parts = token.split(".")
    if len(parts) != 3:
        return False, {"error": "Malformed token structure", "status_code": 401}

    header_b64, payload_b64, sig_b64 = parts

    # Verify signature
    expected_sig = b64url_encode(hmac.new(
        SECRET_KEY.encode("utf-8"),
        f"{header_b64}.{payload_b64}".encode("utf-8"),
        hashlib.sha256
    ).digest())

    if not hmac.compare_digest(sig_b64, expected_sig):
        return False, {"error": "Invalid token signature", "status_code": 401}

    try:
        payload = json.loads(b64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        return False, {"error": "Invalid token payload encoding", "status_code": 401}

    # Verify expiration
    now = int(time.time())
    if payload.get("exp", 0) < now:
        return False, {"error": "Token expired", "status_code": 401}

    return True, payload

def get_app_by_api_key(api_key: str):
    """Retrieves partner application from DB using API key."""
    if not api_key:
        return None
    conn = get_db_connection()
    app = conn.execute("SELECT * FROM partner_apps WHERE api_key = ?", (api_key,)).fetchone()
    conn.close()
    return dict(app) if app else None

def get_app_by_client_id(client_id: str):
    """Retrieves partner application from DB using client_id."""
    if not client_id:
        return None
    conn = get_db_connection()
    app = conn.execute("SELECT * FROM partner_apps WHERE client_id = ?", (client_id,)).fetchone()
    conn.close()
    return dict(app) if app else None

def check_scope(token_payload: dict, required_scope: str):
    """
    Validates if token has required Open Banking scope.
    Returns (has_scope, error_dict).
    """
    granted_scopes = token_payload.get("scopes", [])
    if required_scope not in granted_scopes:
        return False, {
            "error": "insufficient_scope",
            "message": f"Endpoint requires scope '{required_scope}', but token only has '{','.join(granted_scopes)}'",
            "status_code": 403
        }
    return True, None
