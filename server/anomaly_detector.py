"""
SecureBank Connect - AI Anomaly Detection Engine (Scikit-Learn IsolationForest + Heuristic Rules)
"""
import time
import numpy as np
import uuid
import datetime
from sklearn.ensemble import IsolationForest
from server.database import get_db_connection

class AIAnomalyDetector:
    def __init__(self):
        self.model = None
        self.is_trained = False
        self.client_window = {}  # Tracks recent calls per client/IP for sliding-window features
        self.train_baseline_model()

    def train_baseline_model(self):
        """
        Trains IsolationForest on synthetic baseline API telemetry patterns.
        Features: [requests_per_min, error_ratio, scope_violations, avg_latency_ms, payload_size]
        """
        np.random.seed(42)
        n_samples = 1200

        # Normal telemetry distribution
        normal_rpm = np.random.normal(loc=12.0, scale=4.0, size=n_samples).clip(1, 35)
        normal_error_ratio = np.random.beta(a=1, b=30, size=n_samples).clip(0, 0.10)
        normal_violations = np.zeros(n_samples)
        normal_latency = np.random.normal(loc=45.0, scale=15.0, size=n_samples).clip(10, 150)
        normal_payload = np.random.normal(loc=450.0, scale=120.0, size=n_samples).clip(50, 1200)

        X_normal = np.column_stack([normal_rpm, normal_error_ratio, normal_violations, normal_latency, normal_payload])

        # Small percentage of synthetic anomalies for robust boundary tuning
        n_anomalies = 60
        spike_rpm = np.random.uniform(50, 150, size=n_anomalies)
        spike_error_ratio = np.random.uniform(0.30, 0.90, size=n_anomalies)
        spike_violations = np.random.randint(2, 10, size=n_anomalies)
        spike_latency = np.random.uniform(300, 2000, size=n_anomalies)
        spike_payload = np.random.uniform(2500, 10000, size=n_anomalies)

        X_anomaly = np.column_stack([spike_rpm, spike_error_ratio, spike_violations, spike_latency, spike_payload])
        X_train = np.vstack([X_normal, X_anomaly])

        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.06,
            random_state=42
        )
        self.model.fit(X_train)
        self.is_trained = True

    def track_request(self, app_id: str, ip: str, status_code: int, response_time_ms: float, payload_size: int, is_scope_violation: bool = False):
        """
        Records the request in sliding memory window and evaluates anomaly score.
        Returns (is_anomaly: bool, score: float, reasons: list, severity: str)
        """
        now = time.time()
        client_key = f"{app_id or 'anon'}_{ip}"

        if client_key not in self.client_window:
            self.client_window[client_key] = []

        # Keep requests within last 60 seconds
        window = self.client_window[client_key]
        window.append({
            "timestamp": now,
            "status_code": status_code,
            "latency": response_time_ms,
            "payload_size": payload_size,
            "is_violation": is_scope_violation
        })
        self.client_window[client_key] = [r for r in window if now - r["timestamp"] <= 60]
        recent = self.client_window[client_key]

        # Calculate features
        rpm = len(recent)
        errors = sum(1 for r in recent if r["status_code"] >= 400)
        error_ratio = errors / rpm if rpm > 0 else 0.0
        violations = sum(1 for r in recent if r["is_violation"] or r["status_code"] == 403)
        avg_latency = np.mean([r["latency"] for r in recent]) if recent else response_time_ms

        features = np.array([[rpm, error_ratio, violations, avg_latency, payload_size]])

        # 1. Isolation Forest Evaluation
        raw_score = self.model.decision_function(features)[0]  # lower = more anomalous
        # Normalize roughly from [-0.5, 0.5] to [1.0, 0.0]
        ml_anomaly_prob = float(np.clip(0.5 - (raw_score * 1.5), 0.0, 1.0))

        # 2. Heuristic Rule-Based Security Triggers
        reasons = []
        severity = "LOW"
        heuristic_boost = 0.0

        if rpm >= 30:
            reasons.append(f"High-frequency request burst detected ({rpm} req/min)")
            heuristic_boost += 0.35
            severity = "HIGH"

        if rpm >= 60:
            reasons.append(f"Extreme traffic spike ({rpm} req/min) - Potential DDoS or Automated Scraping")
            heuristic_boost += 0.50
            severity = "CRITICAL"

        if violations >= 3:
            reasons.append(f"Multiple permission/scope denials ({violations} violations in 60s)")
            heuristic_boost += 0.40
            severity = "HIGH" if severity != "CRITICAL" else "CRITICAL"

        if error_ratio >= 0.40 and rpm >= 5:
            reasons.append(f"Abnormally high error rate ({error_ratio*100:.1f}%)")
            heuristic_boost += 0.25
            if severity == "LOW":
                severity = "MEDIUM"

        final_score = float(np.clip(ml_anomaly_prob + heuristic_boost, 0.0, 1.0))
        is_anomalous = final_score >= 0.65

        # If anomalous, record a security alert in DB
        if is_anomalous and reasons:
            self._record_security_alert(app_id, severity, "; ".join(reasons), final_score)

        return is_anomalous, round(final_score, 3), reasons, severity

    def _record_security_alert(self, app_id: str, severity: str, description: str, confidence: float):
        """Persists high-confidence security incidents to DB with retry."""
        import time as pytime
        for attempt in range(4):
            conn = None
            try:
                conn = get_db_connection()
                now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                alert_id = f"ALT-AI-{uuid.uuid4().hex[:8].upper()}"
                conn.execute("""
                INSERT INTO alerts (alert_id, created_at, timestamp, app_id, alert_type, severity, description, status, ai_confidence)
                VALUES (?, ?, ?, ?, 'ANOMALOUS_TRAFFIC_PATTERN', ?, ?, 'ACTIVE', ?)
                """, (alert_id, now_iso, now_iso, app_id or "ANONYMOUS", severity, description, round(confidence, 2)))
                conn.commit()
                break
            except Exception as e:
                if attempt == 3:
                    # Final attempt failed
                    pass
                pytime.sleep(0.08)
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

# Global singleton instance
detector = AIAnomalyDetector()
