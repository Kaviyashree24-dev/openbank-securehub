"""
SecureBank Connect - Automated Test Suite
"""
import unittest
import json
import time
from server.database import init_db, get_db_connection
from server.auth import generate_signed_token, verify_token, check_scope
from server.consent import validate_customer_consent, revoke_consent
from server.mock_banking import (
    get_accounts_by_customer, get_account_balances,
    get_transactions_by_account, execute_payment_transfer
)
from server.anomaly_detector import detector
from server.simulator import run_simulation

class TestSecureBankGateway(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_database_seeded(self):
        """Verify DB seeded with synthetic apps, customers, and accounts."""
        conn = get_db_connection()
        apps_count = conn.execute("SELECT COUNT(*) AS c FROM partner_apps").fetchone()["c"]
        accounts_count = conn.execute("SELECT COUNT(*) AS c FROM bank_accounts").fetchone()["c"]
        tx_count = conn.execute("SELECT COUNT(*) AS c FROM bank_transactions").fetchone()["c"]
        conn.close()

        self.assertGreaterEqual(apps_count, 3)
        self.assertGreaterEqual(accounts_count, 5)
        self.assertGreaterEqual(tx_count, 10)

    def test_02_oauth2_token_lifecycle(self):
        """Verify JWT-like HMAC signed token generation and verification."""
        app_id = "app_finpulse_9281"
        scopes = ["accounts:read", "balances:read"]
        token = generate_signed_token(app_id, scopes, customer_id="CUST-1001", expiry_seconds=60)

        # Token should verify successfully
        valid, payload = verify_token(token)
        self.assertTrue(valid)
        self.assertEqual(payload["sub"], app_id)
        self.assertEqual(payload["customer_id"], "CUST-1001")
        self.assertIn("accounts:read", payload["scopes"])

        # Check scope verification
        has_scope, err = check_scope(payload, "accounts:read")
        self.assertTrue(has_scope)

        has_payment_scope, err2 = check_scope(payload, "payments:create")
        self.assertFalse(has_payment_scope)
        self.assertEqual(err2["status_code"], 403)

    def test_03_customer_consent_enforcement(self):
        """Verify explicit customer consent checks and revocation."""
        # Sarah Jenkins has active consent for app_finpulse_9281
        valid, consent = validate_customer_consent("CUST-1001", "app_finpulse_9281", "accounts:read")
        self.assertTrue(valid)
        self.assertEqual(consent["status"], "ACTIVE")

        # Alex Rivera's consent for app_wealth_7730 was pre-seeded as REVOKED
        valid_rev, err = validate_customer_consent("CUST-1003", "app_wealth_7730", "accounts:read")
        self.assertFalse(valid_rev)
        self.assertEqual(err["error"], "consent_revoked")
        self.assertEqual(err["status_code"], 403)

    def test_04_mock_banking_ledger_and_payments(self):
        """Verify synthetic accounts, balances, and payment transfer ledger deduction."""
        acc_from = "ACC-US-8901" # Sarah's checking
        acc_to = "ACC-US-8903"   # Priya's business

        bal_before = get_account_balances(acc_from)
        orig_avail = bal_before["available_balance"]

        # Execute payment transfer of $100
        transfer_amt = 100.0
        success, res = execute_payment_transfer(acc_from, acc_to, transfer_amt, "USD", "Test Transfer")
        self.assertTrue(success)
        self.assertEqual(res["status"], "SETTLED")

        # Verify balance deducted
        bal_after = get_account_balances(acc_from)
        self.assertAlmostEqual(bal_after["available_balance"], orig_avail - transfer_amt, places=2)

    def test_05_ai_anomaly_detection_engine(self):
        """Verify IsolationForest and heuristic rules detect abnormal request patterns."""
        # 1. Normal traffic query
        is_anom, score, reasons, sev = detector.track_request("app_finpulse_9281", "127.0.0.1", 200, 32.0, 450)
        self.assertFalse(is_anom)
        self.assertLess(score, 0.65)

        # 2. Simulate rapid bursts / attack pattern (25 calls in loop)
        anom_detected = False
        for _ in range(25):
            is_anom_burst, burst_score, reasons, sev = detector.track_request("app_rogue_9999", "10.99.1.5", 403, 150.0, 2000, is_scope_violation=True)
            if is_anom_burst:
                anom_detected = True

        self.assertTrue(anom_detected)

    def test_06_traffic_simulator_scenarios(self):
        """Verify the simulator engine runs normal and burst scenarios."""
        sim_norm = run_simulation("normal")
        self.assertEqual(sim_norm["scenario"], "normal")
        self.assertGreater(sim_norm["simulated_requests"], 0)

        sim_burst = run_simulation("burst")
        self.assertEqual(sim_burst["scenario"], "burst")
        self.assertGreater(sim_burst["anomalies_detected"], 0)

if __name__ == "__main__":
    unittest.main()
