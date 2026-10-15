"""
SecureBank Connect - API Gateway Request Handler & Router
"""
import json
import time
import urllib.parse
import mimetypes
from pathlib import Path
from http.server import BaseHTTPRequestHandler
from server.config import STATIC_DIR, DEFAULT_RATE_LIMIT
from server.database import get_db_connection
from server.auth import (
    verify_token, get_app_by_api_key, get_app_by_client_id,
    generate_signed_token, check_scope
)
from server.consent import validate_customer_consent, create_consent, revoke_consent, list_consents
from server.mock_banking import (
    get_accounts_by_customer, get_account_by_id,
    get_account_balances, get_transactions_by_account,
    execute_payment_transfer
)
from server.anomaly_detector import detector
from server.simulator import run_simulation

# In-memory rate limiting dictionary: {client_key: [timestamps]}
RATE_LIMIT_STORE = {}

class OpenBankGatewayHandler(BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        """Custom concise logging."""
        pass  # Suppress default stdout clutter, we have structured audit logs

    def send_json_response(self, status_code: int, data: dict):
        """Sends a JSON response with standard CORS headers."""
        response_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Api-Key, X-Customer-Id")
        self.send_header("X-Gateway-Version", "SecureBank-v1.0")
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        """Handles CORS preflight requests."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Api-Key, X-Customer-Id")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def get_request_body_json(self):
        """Parses JSON request body if present."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 0:
                body = self.rfile.read(length).decode("utf-8")
                return json.loads(body)
        except Exception:
            pass
        return {}

    def authenticate_request(self):
        """
        Extracts auth from Authorization header (Bearer token) or X-Api-Key.
        Returns (is_auth, auth_context_or_error_dict).
        """
        auth_header = self.headers.get("Authorization", "")
        api_key_header = self.headers.get("X-Api-Key", "")

        # 1. Bearer Token Check
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            valid, payload = verify_token(token)
            if not valid:
                return False, payload
            return True, {
                "type": "token",
                "app_id": payload.get("sub"),
                "customer_id": payload.get("customer_id", "CUST-1001"),
                "scopes": payload.get("scopes", []),
                "payload": payload
            }

        # 2. Direct API Key Fallback
        if api_key_header:
            app = get_app_by_api_key(api_key_header)
            if not app:
                return False, {"error": "invalid_api_key", "message": "Provided API key is not registered or valid", "status_code": 401}
            if not app.get("is_active"):
                return False, {"error": "app_suspended", "message": "Partner app is blocked or suspended", "status_code": 403}
            try:
                scopes = json.loads(app["allowed_scopes"])
            except Exception:
                scopes = []
            return True, {
                "type": "api_key",
                "app_id": app["client_id"],
                "customer_id": self.headers.get("X-Customer-Id", "CUST-1001"),
                "scopes": scopes,
                "app": app
            }

        return False, {
            "error": "unauthorized",
            "message": "Missing authentication credentials. Supply 'Authorization: Bearer <token>' or 'X-Api-Key: <key>'",
            "status_code": 401
        }

    def check_rate_limit(self, client_key: str, limit: int = DEFAULT_RATE_LIMIT) -> bool:
        """Enforces sliding-window rate limit (requests per minute)."""
        now = time.time()
        if client_key not in RATE_LIMIT_STORE:
            RATE_LIMIT_STORE[client_key] = []
        # Keep timestamps within 60s
        RATE_LIMIT_STORE[client_key] = [t for t in RATE_LIMIT_STORE[client_key] if now - t <= 60]
        if len(RATE_LIMIT_STORE[client_key]) >= limit:
            return False
        RATE_LIMIT_STORE[client_key].append(now)
        return True

    def log_and_telemetry(self, start_time: float, app_id: str, status_code: int, is_violation: bool = False):
        """Records telemetry into audit log and processes through AI anomaly engine."""
        latency_ms = (time.time() - start_time) * 1000.0
        client_ip = self.client_address[0]
        content_len = int(self.headers.get("Content-Length", 0))

        # Run through AI Anomaly Detector
        is_anom, anom_score, reasons, sev = detector.track_request(
            app_id=app_id,
            ip=client_ip,
            status_code=status_code,
            response_time_ms=latency_ms,
            payload_size=content_len,
            is_scope_violation=is_violation
        )

        import time as pytime
        for attempt in range(4):
            conn = None
            try:
                conn = get_db_connection()
                import datetime
                now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                conn.execute("""
                INSERT INTO api_logs (created_at, timestamp, app_id, method, endpoint, response_status, status_code, ip_address, response_time, response_time_ms, payload_size, is_anomalous, anomaly_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (now_iso, now_iso, app_id, self.command, self.path.split("?")[0], status_code, status_code, client_ip, round(latency_ms, 2), round(latency_ms, 2), content_len, int(is_anom), anom_score))
                conn.commit()
                break
            except Exception as e:
                pytime.sleep(0.05)
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

    # =========================================================================
    # Request Routing
    # =========================================================================
    def do_GET(self):
        start_time = time.time()
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # 1. Static Web Assets
        if not path.startswith("/api/"):
            self.serve_static_file(path)
            return

        app_id = "ANONYMOUS"
        is_violation = False
        status_code = 200

        try:
            # Monitoring Endpoints (Unprotected or admin internal)
            if path == "/api/v1/monitoring/metrics":
                data = self.handle_get_metrics()
                self.send_json_response(200, data)
                return

            if path == "/api/v1/monitoring/logs":
                limit = int(query.get("limit", [50])[0])
                data = self.handle_get_logs(limit)
                self.send_json_response(200, data)
                return

            if path == "/api/v1/monitoring/alerts":
                data = self.handle_get_alerts()
                self.send_json_response(200, data)
                return

            if path == "/api/v1/developers":
                conn = get_db_connection()
                devs = [dict(r) for r in conn.execute("SELECT * FROM developers").fetchall()]
                conn.close()
                self.send_json_response(200, {"developers": devs})
                return

            if path == "/api/v1/users":
                conn = get_db_connection()
                users = [dict(r) for r in conn.execute("SELECT * FROM users").fetchall()]
                conn.close()
                self.send_json_response(200, {"users": users})
                return

            if path == "/api/v1/apps":
                data = self.handle_list_apps()
                self.send_json_response(200, data)
                return

            if path == "/api/v1/consents":
                cust_id = query.get("customer_id", [None])[0]
                data = list_consents(cust_id)
                self.send_json_response(200, {"consents": data})
                return

            # Open Banking Core APIs (Require Auth & Consent Verification)
            is_auth, auth_ctx = self.authenticate_request()
            if not is_auth:
                status_code = auth_ctx.get("status_code", 401)
                self.send_json_response(status_code, auth_ctx)
                self.log_and_telemetry(start_time, "UNAUTHORIZED", status_code, is_violation=True)
                return

            app_id = auth_ctx["app_id"]
            customer_id = auth_ctx["customer_id"]

            # Rate limit check
            if not self.check_rate_limit(f"{app_id}_{self.client_address[0]}"):
                status_code = 429
                self.send_json_response(429, {"error": "rate_limit_exceeded", "message": "Too many requests. Limit is 60 req/min."})
                self.log_and_telemetry(start_time, app_id, 429, is_violation=True)
                return

            # Endpoint: GET /api/v1/accounts
            if path == "/api/v1/accounts":
                has_scope, scope_err = check_scope(auth_ctx, "accounts:read")
                if not has_scope:
                    is_violation = True
                    status_code = 403
                    self.send_json_response(403, scope_err)
                    return

                has_consent, consent_err = validate_customer_consent(customer_id, app_id, "accounts:read")
                if not has_consent:
                    is_violation = True
                    status_code = 403
                    self.send_json_response(403, consent_err)
                    return

                accounts = get_accounts_by_customer(customer_id)
                self.send_json_response(200, {
                    "customer_id": customer_id,
                    "accounts": accounts,
                    "count": len(accounts)
                })
                return

            # Endpoint: GET /api/v1/accounts/<account_id>/balances
            if path.startswith("/api/v1/accounts/") and path.endswith("/balances"):
                parts = path.strip("/").split("/")
                account_id = parts[3]

                has_scope, scope_err = check_scope(auth_ctx, "balances:read")
                if not has_scope:
                    is_violation = True
                    status_code = 403
                    self.send_json_response(403, scope_err)
                    return

                has_consent, consent_err = validate_customer_consent(customer_id, app_id, "balances:read")
                if not has_consent:
                    is_violation = True
                    status_code = 403
                    self.send_json_response(403, consent_err)
                    return

                balances = get_account_balances(account_id)
                if not balances:
                    status_code = 404
                    self.send_json_response(404, {"error": "account_not_found", "message": f"Account '{account_id}' does not exist"})
                    return

                self.send_json_response(200, balances)
                return

            # Endpoint: GET /api/v1/accounts/<account_id>/transactions
            if path.startswith("/api/v1/accounts/") and path.endswith("/transactions"):
                parts = path.strip("/").split("/")
                account_id = parts[3]

                has_scope, scope_err = check_scope(auth_ctx, "transactions:read")
                if not has_scope:
                    is_violation = True
                    status_code = 403
                    self.send_json_response(403, scope_err)
                    return

                has_consent, consent_err = validate_customer_consent(customer_id, app_id, "transactions:read")
                if not has_consent:
                    is_violation = True
                    status_code = 403
                    self.send_json_response(403, consent_err)
                    return

                limit = int(query.get("limit", [20])[0])
                category = query.get("category", [None])[0]
                txs = get_transactions_by_account(account_id, limit, category)
                self.send_json_response(200, {
                    "account_id": account_id,
                    "transactions": txs,
                    "total": len(txs)
                })
                return

            # Default 404
            status_code = 404
            self.send_json_response(404, {"error": "not_found", "message": f"Resource '{path}' does not exist"})

        except Exception as e:
            status_code = 500
            self.send_json_response(500, {"error": "internal_error", "message": str(e)})
        finally:
            self.log_and_telemetry(start_time, app_id, status_code, is_violation=is_violation)

    def do_POST(self):
        start_time = time.time()
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        body = self.get_request_body_json()

        app_id = "ANONYMOUS"
        is_violation = False
        status_code = 200

        try:
            # 1. OAuth2 Token Exchange: POST /api/v1/oauth/token
            if path == "/api/v1/oauth/token":
                client_id = body.get("client_id")
                client_secret = body.get("client_secret")
                customer_id = body.get("customer_id", "CUST-1001")
                requested_scopes = body.get("scopes", ["accounts:read", "balances:read"])

                app = get_app_by_client_id(client_id)
                if not app or app["client_secret"] != client_secret:
                    status_code = 401
                    self.send_json_response(401, {"error": "invalid_client", "message": "Client credentials are not valid"})
                    return

                if not app.get("is_active"):
                    status_code = 403
                    self.send_json_response(403, {"error": "app_blocked", "message": "Partner app is blocked or suspended by administrator"})
                    return

                app_id = client_id
                # Filter requested scopes to those allowed for this partner app
                try:
                    allowed = json.loads(app["allowed_scopes"])
                except Exception:
                    allowed = []
                final_scopes = [s for s in requested_scopes if s in allowed]

                token = generate_signed_token(client_id, final_scopes, customer_id)
                self.send_json_response(200, {
                    "access_token": token,
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": " ".join(final_scopes),
                    "customer_id": customer_id
                })
                return

            # 2. Register Partner App: POST /api/v1/apps
            if path == "/api/v1/apps":
                name = body.get("name")
                scopes = body.get("scopes", ["accounts:read", "balances:read"])
                if not name:
                    status_code = 400
                    self.send_json_response(400, {"error": "bad_request", "message": "App 'name' is required"})
                    return

                import uuid, datetime
                cid = f"app_{uuid.uuid4().hex[:8]}"
                sec = f"sec_live_{uuid.uuid4().hex[:12]}"
                key = f"sb_live_{uuid.uuid4().hex[:16]}"
                now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

                conn = get_db_connection()
                conn.execute("""
                INSERT INTO partner_apps (name, client_id, client_secret, api_key, allowed_scopes, rate_limit, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, 60, 1, ?)
                """, (name, cid, sec, key, json.dumps(scopes), now_str))
                conn.commit()
                conn.close()

                self.send_json_response(201, {
                    "name": name,
                    "client_id": cid,
                    "client_secret": sec,
                    "api_key": key,
                    "allowed_scopes": scopes,
                    "rate_limit": 60,
                    "status": "ACTIVE"
                })
                return

            # 3. Toggle App Status (Block / Unblock): POST /api/v1/apps/<id>/toggle
            if path.startswith("/api/v1/apps/") and path.endswith("/toggle"):
                parts = path.strip("/").split("/")
                app_client_id = parts[3]
                conn = get_db_connection()
                app = conn.execute("SELECT * FROM partner_apps WHERE client_id = ?", (app_client_id,)).fetchone()
                if not app:
                    conn.close()
                    status_code = 404
                    self.send_json_response(404, {"error": "app_not_found"})
                    return
                new_status = 0 if app["is_active"] == 1 else 1
                conn.execute("UPDATE partner_apps SET is_active = ? WHERE client_id = ?", (new_status, app_client_id))
                conn.commit()
                conn.close()
                self.send_json_response(200, {
                    "client_id": app_client_id,
                    "is_active": new_status,
                    "status_label": "ACTIVE" if new_status == 1 else "BLOCKED"
                })
                return

            # 4. Create Customer Consent: POST /api/v1/consents
            if path == "/api/v1/consents":
                customer_id = body.get("customer_id")
                target_app_id = body.get("app_id")
                scopes = body.get("scopes", ["accounts:read", "balances:read"])
                if not customer_id or not target_app_id:
                    status_code = 400
                    self.send_json_response(400, {"error": "bad_request", "message": "customer_id and app_id are required"})
                    return
                consent = create_consent(customer_id, target_app_id, scopes)
                self.send_json_response(201, consent)
                return

            # 5. Revoke Customer Consent: POST /api/v1/consents/<id>/revoke
            if path.startswith("/api/v1/consents/") and path.endswith("/revoke"):
                parts = path.strip("/").split("/")
                consent_id = parts[3]
                consent = revoke_consent(consent_id)
                if not consent:
                    status_code = 404
                    self.send_json_response(404, {"error": "consent_not_found"})
                    return
                self.send_json_response(200, {
                    "message": "Consent explicitly revoked by customer",
                    "consent": consent
                })
                return

            # 6. Resolve Security Alert: POST /api/v1/monitoring/alerts/<id>/resolve
            if path.startswith("/api/v1/monitoring/alerts/") and path.endswith("/resolve"):
                parts = path.strip("/").split("/")
                alert_id = parts[4]
                conn = get_db_connection()
                conn.execute("UPDATE alerts SET status = 'RESOLVED' WHERE alert_id = ?", (alert_id,))
                conn.commit()
                conn.close()
                self.send_json_response(200, {"alert_id": alert_id, "status": "RESOLVED"})
                return

            # 6b. Suspend App Key from Alert (Implements Admin Alert -> Suspend test key -> Auth & Consent Checks feedback loop)
            if path.startswith("/api/v1/monitoring/alerts/") and path.endswith("/suspend-app"):
                parts = path.strip("/").split("/")
                alert_id = parts[4]
                conn = get_db_connection()
                alert_row = conn.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,)).fetchone()
                if not alert_row:
                    conn.close()
                    status_code = 404
                    self.send_json_response(404, {"error": "alert_not_found"})
                    return
                target_app_id = alert_row["app_id"]
                conn.execute("UPDATE applications SET is_active = 0, status = 'SUSPENDED' WHERE client_id = ?", (target_app_id,))
                conn.execute("UPDATE alerts SET status = 'RESOLVED' WHERE alert_id = ?", (alert_id,))
                conn.commit()
                conn.close()
                self.send_json_response(200, {
                    "alert_id": alert_id,
                    "target_app_id": target_app_id,
                    "status": "SUSPENDED",
                    "message": f"Partner app '{target_app_id}' suspended. Future requests will be blocked at Auth & Consent Checks."
                })
                return

            # 7. Traffic Simulator Trigger: POST /api/v1/simulate/traffic
            if path == "/api/v1/simulate/traffic":
                scenario = body.get("scenario", "normal")
                sim_res = run_simulation(scenario)
                self.send_json_response(200, sim_res)
                return

            # 8. Open Banking Payment Initiation: POST /api/v1/payments
            if path == "/api/v1/payments":
                is_auth, auth_ctx = self.authenticate_request()
                if not is_auth:
                    status_code = auth_ctx.get("status_code", 401)
                    self.send_json_response(status_code, auth_ctx)
                    self.log_and_telemetry(start_time, "UNAUTHORIZED", status_code, is_violation=True)
                    return

                app_id = auth_ctx["app_id"]
                customer_id = auth_ctx["customer_id"]

                # Check payment scope
                has_scope, scope_err = check_scope(auth_ctx, "payments:create")
                if not has_scope:
                    is_violation = True
                    status_code = 403
                    self.send_json_response(403, scope_err)
                    return

                # Check customer consent for payments
                has_consent, consent_err = validate_customer_consent(customer_id, app_id, "payments:create")
                if not has_consent:
                    is_violation = True
                    status_code = 403
                    self.send_json_response(403, consent_err)
                    return

                from_acc = body.get("from_account_id")
                to_acc = body.get("to_account_id")
                amount = float(body.get("amount", 0))
                currency = body.get("currency", "USD")
                reference = body.get("reference", "OpenBanking API Payment")

                if not from_acc or not to_acc or amount <= 0:
                    status_code = 400
                    self.send_json_response(400, {"error": "bad_request", "message": "from_account_id, to_account_id, and positive amount are required"})
                    return

                ok, payment_res = execute_payment_transfer(from_acc, to_acc, amount, currency, reference)
                if not ok:
                    status_code = payment_res.get("status_code", 400)
                    self.send_json_response(status_code, payment_res)
                    return

                status_code = 201
                self.send_json_response(201, payment_res)
                return

            # Default 404
            status_code = 404
            self.send_json_response(404, {"error": "not_found", "message": f"Resource '{path}' does not exist"})

        except Exception as e:
            status_code = 500
            self.send_json_response(500, {"error": "internal_error", "message": str(e)})
        finally:
            self.log_and_telemetry(start_time, app_id, status_code, is_violation=is_violation)

    # =========================================================================
    # Monitoring Handlers
    # =========================================================================
    def handle_get_metrics(self):
        conn = get_db_connection()
        cursor = conn.cursor()

        total_requests = cursor.execute("SELECT COUNT(*) AS c FROM audit_logs").fetchone()["c"]
        total_errors = cursor.execute("SELECT COUNT(*) AS c FROM audit_logs WHERE status_code >= 400").fetchone()["c"]
        anomalies_count = cursor.execute("SELECT COUNT(*) AS c FROM audit_logs WHERE is_anomalous = 1").fetchone()["c"]
        avg_latency = cursor.execute("SELECT AVG(response_time_ms) AS a FROM audit_logs").fetchone()["a"] or 34.5
        active_apps = cursor.execute("SELECT COUNT(*) AS c FROM partner_apps WHERE is_active = 1").fetchone()["c"]
        active_consents = cursor.execute("SELECT COUNT(*) AS c FROM consents WHERE status = 'ACTIVE'").fetchone()["c"]

        # Status code breakdown
        status_breakdown = {}
        for row in cursor.execute("SELECT status_code, COUNT(*) AS count FROM audit_logs GROUP BY status_code"):
            status_breakdown[str(row["status_code"])] = row["count"]

        conn.close()

        error_rate = (total_errors / total_requests * 100.0) if total_requests > 0 else 0.0

        return {
            "total_requests": total_requests,
            "error_rate_pct": round(error_rate, 2),
            "anomalies_detected": anomalies_count,
            "avg_latency_ms": round(avg_latency, 1),
            "active_partner_apps": active_apps,
            "active_consents": active_consents,
            "gateway_uptime_pct": 99.98,
            "status_code_breakdown": status_breakdown
        }

    def handle_get_logs(self, limit: int = 50):
        conn = get_db_connection()
        rows = conn.execute("""
        SELECT * FROM audit_logs
        ORDER BY id DESC LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return {"logs": [dict(r) for r in rows]}

    def handle_get_alerts(self):
        conn = get_db_connection()
        rows = conn.execute("""
        SELECT * FROM security_alerts
        ORDER BY id DESC LIMIT 30
        """).fetchall()
        conn.close()
        return {"alerts": [dict(r) for r in rows]}

    def handle_list_apps(self):
        conn = get_db_connection()
        rows = conn.execute("""
        SELECT a.*, COALESCE(a.app_name, a.name) AS name, d.name AS developer_name, d.company_name
        FROM applications a
        LEFT JOIN developers d ON a.developer_id = d.developer_id
        ORDER BY a.rowid ASC
        """).fetchall()
        conn.close()
        return {"apps": [dict(r) for r in rows]}

    # =========================================================================
    # Static File Serving
    # =========================================================================
    def serve_static_file(self, path: str):
        if path in ["", "/"]:
            file_path = STATIC_DIR / "index.html"
        else:
            file_path = STATIC_DIR / path.lstrip("/")

        # Prevent directory traversal attacks
        try:
            resolved = file_path.resolve()
            if not str(resolved).startswith(str(STATIC_DIR.resolve())):
                self.send_error(403, "Forbidden")
                return
        except Exception:
            self.send_error(404, "File Not Found")
            return

        if not file_path.exists() or not file_path.is_file():
            # Fallback to index.html for SPA routing
            file_path = STATIC_DIR / "index.html"

        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            mime_type = "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", f"{mime_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")
