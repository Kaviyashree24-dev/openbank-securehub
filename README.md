# SecureBank Connect · One Secure Gateway

> **Category:** Open Banking & API Ecosystems  
> **Tagline:** One Secure Gateway. Smarter Banking Integrations.  
> **Official Problem Statement:** *"Develop a secure open-banking API platform that enables authorized partners to integrate approved banking capabilities and build value-added services through documented, governed interfaces."*

---

## 🌟 Executive Summary

**SecureBank Connect** is a complete, production-grade Open Banking Gateway and developer platform. It allows approved fintech partner applications (personal finance managers, budgeting apps, invoicing platforms) to access simulated banking services through one secure, standardized gateway.

Every single request is governed by **explicit customer consent**, **scoped OAuth2 permissions**, and continuous **AI-assisted anomaly detection** powered by Scikit-Learn's `IsolationForest` machine learning algorithm.

---

## 🏛️ Architecture & Core Request Flow

```
+------------------------+
|  Fintech Partner Apps  | (FinPulse, QuickInvoice, WealthTrack)
+-----------+------------+
            | 
            v  [HTTPS / OAuth2 Bearer Token / X-Api-Key]
+--------------------------------------------------------------+
|                     SecureBank API Gateway                   |
|  - Rate Limiting (60 req/min)                                |
|  - Token Signature & Expiry Verification                     |
|  - Granular Scope Checking (accounts, balances, payments)     |
+------------------------------+-------------------------------+
                               |
         +---------------------+---------------------+
         |                                           |
         v                                           v
+-------------------------------+       +-------------------------------+
|  Customer Consent Engine      |       |  AI Anomaly Detection Engine  |
|  - Checks customer grant      |       |  - Scikit-Learn IsolationForest
|  - Immediate 403 on revoke    |       |  - Heuristic Security Rules   |
|  - Expiry enforcement         |       |  - Real-time Threat Alerts    |
+---------------+---------------+       +---------------+---------------+
                |                                       |
                v                                       v
+-------------------------------+       +-------------------------------+
|     Mock Banking Services     |       |    Monitoring Dashboard       |
|  - Synthetic Accounts         |       |  - Live Request Audit Logs    |
|  - Balances & Transactions    |       |  - HTTP Status Breakdown      |
|  - Payment Settlement Ledger  |       |  - Attack Pattern Simulator   |
+-------------------------------+       +-------------------------------+
```

---

## 🚀 Key Features

| Feature | Description | Problem Addressed |
|---|---|---|
| **Standardized API Gateway** | Uniform REST interfaces for accounts, balances, transactions, and payments. | Inconsistent, custom adapter code per bank |
| **Developer Portal** | Self-service registration, credential issuance (Client ID, API Key, Secret), and interactive API sandbox. | Difficult partner onboarding |
| **Explicit Customer Consent** | Customers see which apps have access, inspect granted scopes, and can revoke consent with 1 click. | Weak consent management & privacy risks |
| **Synthetic Sandbox** | Zero-risk synthetic data ledger with realistic customers, checking/savings/business accounts, and transactions. | No safe environment to test integrations |
| **AI Anomaly Detection** | Scikit-Learn `IsolationForest` ML engine detects rapid traffic spikes, scraping, scope tampering, and probing. | Limited visibility and delayed threat awareness |
| **Attack Simulator** | Built-in simulator to trigger normal traffic, DDoS bursts, unauthorized scope attacks, or revoked consent probes. | Demonstrating live defense & resilience |

---

## ⚡ Quick Start

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.11)
- Dependencies: `scikit-learn`, `numpy`, `scipy`

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Run the Server
```powershell
python run.py
```
Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 💻 VS Code Integration

This project is pre-configured for full VS Code pair-programming:

1. **One-Click Debugging (`F5`)**:
   - Open VS Code: `code .`
   - Press `F5` to start the Gateway Server with live debugging and breakpoints.
   - Or select `"🧪 Run Gateway Test Suite"` in the Run & Debug pane.
2. **VS Code Tasks (`Ctrl + Shift + B`)**:
   - `Start SecureBank Gateway` (Default Build Task)
   - `Run Test Suite` (Default Test Task)
   - `Install Dependencies`
   - `Git Status`
3. **In-Editor REST API Testing**:
   - Open [`api_requests.http`](file:///c:/Users/nithi/Downloads/openbank-securehub/api_requests.http)
   - Click **"Send Request"** above any endpoint to test with the VS Code REST Client extension.

---

## 🐙 Git Integration & Connecting to Remote

### Connect to your GitHub / GitLab repository:

```powershell
# 1. Initialize and verify git status
git status

# 2. Add your GitHub remote repository (replace with your repo URL)
git remote add origin https://github.com/<your-username>/<your-repo-name>.git

# 3. Rename branch to main (if preferred)
git branch -M main

# 4. Push your code to remote
git push -u origin main
```

---

## 🧪 Running Automated Tests

Run the full verification suite covering authentication, consent enforcement, mock ledger payments, and AI anomaly detection:

```powershell
python -m unittest tests/test_gateway.py
```

---

## 📂 Project Structure

```
openbank-securehub/
├── .vscode/
│   ├── launch.json          # F5 Debugger launcher for VS Code
│   ├── tasks.json           # VS Code Build & Test tasks
│   ├── settings.json        # Workspace Python & Editor settings
│   └── extensions.json      # Recommended VS Code extensions
├── server/
│   ├── config.py            # Global settings & constants
│   ├── database.py          # SQLite schema, tables & synthetic data seeder
│   ├── auth.py              # OAuth2 HMAC tokens & scope checking
│   ├── consent.py           # Customer consent lifecycle (grant/check/revoke)
│   ├── mock_banking.py      # Synthetic accounts, balances, transactions & payments
│   ├── anomaly_detector.py  # Scikit-Learn IsolationForest & AI threat scorer
│   ├── gateway.py           # HTTP Request handler, rate limiter & router
│   └── simulator.py         # Real-time traffic & attack pattern generator
├── static/
│   ├── index.html           # Full Single-Page Application (5 views)
│   ├── css/
│   │   └── style.css        # Premium dark glassmorphism fintech UI
│   └── js/
│       └── app.js           # Interactive controller, live charts & telemetry
├── tests/
│   └── test_gateway.py      # Automated test suite
├── api_requests.http        # VS Code REST Client test script
├── requirements.txt         # Minimal Python requirements
├── .gitignore               # Configured gitignore
├── run.py                   # Master entrypoint
└── README.md                # Project documentation
```

---

## 🔒 Security & Open Banking Compliance Summary

- **Scoped Access**: `accounts:read`, `balances:read`, `transactions:read`, `payments:create`.
- **Token Format**: Cryptographically signed HMAC-SHA256 Bearer tokens with strict 1-hour expiration.
- **Explicit Revocation**: If a customer revokes consent, subsequent requests return `403 Forbidden` with an audit trail entry.
- **AI Telemetry**: Multi-factor feature vectors fed into an `IsolationForest` model to detect anomalies before damage occurs.
