"""
SecureBank Connect - Realistic Synthetic Traffic & Attack Pattern Simulator
"""
import time
import random
import datetime
from server.database import get_db_connection
from server.anomaly_detector import detector

def run_simulation(scenario: str):
    """
    Simulates different traffic scenarios to demonstrate the API Gateway,
    Governance filters, and AI Anomaly Detection in real time.
    Scenarios:
      - 'normal': Regular fintech app polling accounts and balances
      - 'burst': Spike in traffic triggering rate limiting and AI anomaly
      - 'scope_attack': Unauthorized payment and transaction attempts without consent
      - 'revoked_probe': Probing accounts of customers who explicitly revoked consent
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now(datetime.timezone.utc)
    results = []

    if scenario == "normal":
        # Simulate 8 legitimate requests from registered partner apps
        apps = ["app_finpulse_9281", "app_quickinv_4412"]
        endpoints = [
            ("/api/v1/accounts", "GET", 200, 32.5),
            ("/api/v1/accounts/ACC-US-8901/balances", "GET", 200, 28.1),
            ("/api/v1/accounts/ACC-US-8901/transactions", "GET", 200, 45.0),
            ("/api/v1/accounts/ACC-US-8903/balances", "GET", 200, 24.8),
        ]
        for _ in range(8):
            app = random.choice(apps)
            ep, method, status, lat = random.choice(endpoints)
            payload_sz = random.randint(200, 800)
            latency = lat + random.uniform(-5, 15)
            is_anom, score, reasons, sev = detector.track_request(app, "192.168.1.45", status, latency, payload_sz)
            
            cursor.execute("""
            INSERT INTO api_logs (created_at, timestamp, app_id, method, endpoint, response_status, status_code, ip_address, response_time, response_time_ms, payload_size, is_anomalous, anomaly_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, '192.168.1.45', ?, ?, ?, ?, ?)
            """, (now.isoformat(), now.isoformat(), app, method, ep, status, status, round(latency, 1), round(latency, 1), payload_sz, int(is_anom), score))
            results.append({"app": app, "endpoint": ep, "status": status, "score": score, "anomalous": is_anom})

    elif scenario == "burst":
        # Simulate aggressive burst of 28 rapid requests in 2 seconds (DDoS / Scraping attempt)
        app = "app_wealth_7730"
        for i in range(25):
            ep = "/api/v1/accounts/ACC-US-8901/transactions"
            status = 200 if i < 15 else 429 # hits rate limit
            latency = random.uniform(110.0, 320.0)
            payload_sz = random.randint(800, 1500)
            is_anom, score, reasons, sev = detector.track_request(app, "10.0.4.88", status, latency, payload_sz)
            
            cursor.execute("""
            INSERT INTO api_logs (created_at, timestamp, app_id, method, endpoint, response_status, status_code, ip_address, response_time, response_time_ms, payload_size, is_anomalous, anomaly_score)
            VALUES (?, ?, ?, 'GET', ?, ?, ?, '10.0.4.88', ?, ?, ?, ?, ?)
            """, (now.isoformat(), now.isoformat(), app, ep, status, status, round(latency, 1), round(latency, 1), payload_sz, int(is_anom), score))
            results.append({"app": app, "endpoint": ep, "status": status, "score": score, "anomalous": is_anom, "reasons": reasons})

    elif scenario == "scope_attack":
        # Simulate unauthorized payments / scope tampering attempts
        app = "app_finpulse_9281" # FinPulse does NOT have 'payments:create' scope!
        for i in range(7):
            ep = "/api/v1/payments"
            status = 403 # Forbidden: insufficient_scope
            latency = random.uniform(22.0, 50.0)
            payload_sz = 350
            is_anom, score, reasons, sev = detector.track_request(app, "172.16.0.12", status, latency, payload_sz, is_scope_violation=True)
            
            cursor.execute("""
            INSERT INTO api_logs (created_at, timestamp, app_id, method, endpoint, response_status, status_code, ip_address, response_time, response_time_ms, payload_size, is_anomalous, anomaly_score)
            VALUES (?, ?, ?, 'POST', ?, ?, ?, '172.16.0.12', ?, ?, ?, ?, ?)
            """, (now.isoformat(), now.isoformat(), app, ep, status, status, round(latency, 1), round(latency, 1), payload_sz, int(is_anom), score))
            results.append({"app": app, "endpoint": ep, "status": status, "score": score, "anomalous": is_anom, "reasons": reasons})

    elif scenario == "revoked_probe":
        # Simulate attempts to access Alex Rivera's (CUST-1003) data whose consent is revoked
        app = "app_wealth_7730"
        for i in range(6):
            ep = "/api/v1/accounts/ACC-US-8905/balances"
            status = 403 # Forbidden: consent_revoked
            latency = random.uniform(25.0, 48.0)
            payload_sz = 210
            is_anom, score, reasons, sev = detector.track_request(app, "192.168.1.99", status, latency, payload_sz, is_scope_violation=True)
            
            cursor.execute("""
            INSERT INTO api_logs (created_at, timestamp, app_id, method, endpoint, response_status, status_code, ip_address, response_time, response_time_ms, payload_size, is_anomalous, anomaly_score)
            VALUES (?, ?, ?, 'GET', ?, ?, ?, '192.168.1.99', ?, ?, ?, ?, ?)
            """, (now.isoformat(), now.isoformat(), app, ep, status, status, round(latency, 1), round(latency, 1), payload_sz, int(is_anom), score))
            results.append({"app": app, "endpoint": ep, "status": status, "score": score, "anomalous": is_anom, "reasons": reasons})

    conn.commit()
    conn.close()

    return {
        "scenario": scenario,
        "simulated_requests": len(results),
        "anomalies_detected": sum(1 for r in results if r.get("anomalous")),
        "details": results[:5]
    }
