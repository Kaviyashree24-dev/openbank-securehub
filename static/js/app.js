/**
 * SecureBank Connect - Interactive Frontend Engine
 * Works seamlessly both with local Python Gateway (127.0.0.1:8000)
 * and in static preview / GitHub Pages with an in-browser sandbox engine.
 */

// Global State
let registeredApps = [];
let chartInstance = null;
let pollTimer = null;
let isMockMode = false;

// =========================================================================
// Synthetic In-Memory Mock Gateway Database (for GitHub Pages Demo)
// =========================================================================
const mockDb = {
    apps: [
        {
            client_id: "app_finpulse_9281",
            client_secret: "sec_live_9a8f7c6e5d4b",
            api_key: "sb_live_finpulse_k9281a",
            name: "FinPulse Smart Budgeting",
            developer_name: "Alex Chen",
            company_name: "FinPulse Technologies Inc.",
            allowed_scopes: JSON.stringify(["accounts:read", "balances:read", "transactions:read"]),
            rate_limit: 60,
            is_active: 1
        },
        {
            client_id: "app_quickinv_4412",
            client_secret: "sec_live_3b2a1c9e8f7d",
            api_key: "sb_live_quickinv_m4412x",
            name: "QuickInvoice Pro",
            developer_name: "Elena Rostova",
            company_name: "QuickInvoice Software Group",
            allowed_scopes: JSON.stringify(["accounts:read", "balances:read", "payments:create"]),
            rate_limit: 60,
            is_active: 1
        },
        {
            client_id: "app_wealth_7730",
            client_secret: "sec_live_7e8d9c0a1b2c",
            api_key: "sb_live_wealth_p7730q",
            name: "WealthTrack AI Analytics",
            developer_name: "Marcus Vance",
            company_name: "WealthTrack Analytics Corp",
            allowed_scopes: JSON.stringify(["accounts:read", "balances:read", "transactions:read"]),
            rate_limit: 90,
            is_active: 1
        }
    ],

    customers: [
        { customer_id: "CUST-1001", name: "Sarah Jenkins", email: "sarah.jenkins@example.com", phone: "+1-415-555-0192" },
        { customer_id: "CUST-1002", name: "Priya Sharma", email: "priya.sharma@example.com", phone: "+1-415-555-0144" },
        { customer_id: "CUST-1003", name: "Alex Rivera", email: "alex.rivera@example.com", phone: "+1-415-555-0188" }
    ],

    accounts: [
        { account_id: "ACC-US-8901", customer_id: "CUST-1001", account_number: "40928192801", account_type: "CHECKING", bank_name: "SecureBank Digital Trust", currency: "USD", balance: 14850.50, available_balance: 14250.50, status: "ACTIVE" },
        { account_id: "ACC-US-8902", customer_id: "CUST-1001", account_number: "40928192802", account_type: "SAVINGS", bank_name: "SecureBank Digital Trust", currency: "USD", balance: 54300.00, available_balance: 54300.00, status: "ACTIVE" },
        { account_id: "ACC-US-8903", customer_id: "CUST-1002", account_number: "50192837401", account_type: "BUSINESS_OPERATING", bank_name: "SecureBank Commercial", currency: "USD", balance: 128450.75, available_balance: 126900.00, status: "ACTIVE" },
        { account_id: "ACC-US-8904", customer_id: "CUST-1002", account_number: "50192837402", account_type: "SAVINGS_RESERVE", bank_name: "SecureBank Commercial", currency: "USD", balance: 85000.00, available_balance: 85000.00, status: "ACTIVE" },
        { account_id: "ACC-US-8905", customer_id: "CUST-1003", account_number: "60293847101", account_type: "CHECKING", bank_name: "SecureBank Community", currency: "USD", balance: 6200.20, available_balance: 5950.00, status: "ACTIVE" }
    ],

    transactions: [
        { transaction_id: "TXN-2026-1001", account_id: "ACC-US-8901", timestamp: new Date(Date.now() - 3600000 * 5).toISOString(), type: "DEBIT", amount: 342.50, description: "Amazon Web Services Cloud", category: "Cloud Infrastructure", status: "SETTLED", reference: "AWS-INV-9921", counterparty: "Amazon AWS" },
        { transaction_id: "TXN-2026-1002", account_id: "ACC-US-8901", timestamp: new Date(Date.now() - 3600000 * 24).toISOString(), type: "CREDIT", amount: 4500.00, description: "Payroll Direct Deposit - TechCorp", category: "Salary", status: "SETTLED", reference: "DIR-DEP-8831", counterparty: "TechCorp Global" },
        { transaction_id: "TXN-2026-1003", account_id: "ACC-US-8901", timestamp: new Date(Date.now() - 3600000 * 48).toISOString(), type: "DEBIT", amount: 14.85, description: "Starbucks Coffee #2819", category: "Food & Dining", status: "SETTLED", reference: "POS-STB-0192", counterparty: "Starbucks Corp" },
        { transaction_id: "TXN-2026-1004", account_id: "ACC-US-8903", timestamp: new Date(Date.now() - 3600000 * 12).toISOString(), type: "CREDIT", amount: 18500.00, description: "Client Retainer - Nexus Enterprise", category: "Revenue", status: "SETTLED", reference: "INV-2026-891", counterparty: "Nexus Enterprise LLC" },
        { transaction_id: "TXN-2026-1005", account_id: "ACC-US-8903", timestamp: new Date(Date.now() - 3600000 * 72).toISOString(), type: "DEBIT", amount: 540.00, description: "Google Cloud Suite", category: "Software / SaaS", status: "SETTLED", reference: "GOOG-66321", counterparty: "Google LLC" }
    ],

    consents: [
        {
            consent_id: "CNS-9011-SARAH",
            customer_id: "CUST-1001",
            customer_name: "Sarah Jenkins",
            app_id: "app_finpulse_9281",
            app_name: "FinPulse Smart Budgeting",
            scopes: JSON.stringify(["accounts:read", "balances:read", "transactions:read"]),
            status: "ACTIVE",
            expires_at: new Date(Date.now() + 86400000 * 90).toISOString()
        },
        {
            consent_id: "CNS-9012-PRIYA",
            customer_id: "CUST-1002",
            customer_name: "Priya Sharma",
            app_id: "app_quickinv_4412",
            app_name: "QuickInvoice Pro",
            scopes: JSON.stringify(["accounts:read", "balances:read", "payments:create"]),
            status: "ACTIVE",
            expires_at: new Date(Date.now() + 86400000 * 180).toISOString()
        },
        {
            consent_id: "CNS-9013-ALEX",
            customer_id: "CUST-1003",
            customer_name: "Alex Rivera",
            app_id: "app_wealth_7730",
            app_name: "WealthTrack AI Analytics",
            scopes: JSON.stringify(["accounts:read", "balances:read"]),
            status: "REVOKED",
            expires_at: new Date(Date.now() + 86400000 * 30).toISOString()
        }
    ],

    logs: [
        { timestamp: new Date(Date.now() - 1000 * 15).toISOString(), app_id: "app_finpulse_9281", method: "GET", endpoint: "/api/v1/accounts", status_code: 200, response_time_ms: 34.2, anomaly_score: 0.042, is_anomalous: 0 },
        { timestamp: new Date(Date.now() - 1000 * 45).toISOString(), app_id: "app_finpulse_9281", method: "GET", endpoint: "/api/v1/accounts/ACC-US-8901/balances", status_code: 200, response_time_ms: 28.5, anomaly_score: 0.038, is_anomalous: 0 },
        { timestamp: new Date(Date.now() - 1000 * 90).toISOString(), app_id: "app_wealth_7730", method: "GET", endpoint: "/api/v1/accounts", status_code: 403, response_time_ms: 18.2, anomaly_score: 0.310, is_anomalous: 0 },
        { timestamp: new Date(Date.now() - 1000 * 180).toISOString(), app_id: "app_quickinv_4412", method: "POST", endpoint: "/api/v1/payments", status_code: 201, response_time_ms: 68.4, anomaly_score: 0.095, is_anomalous: 0 },
        { timestamp: new Date(Date.now() - 1000 * 320).toISOString(), app_id: "ANONYMOUS", method: "GET", endpoint: "/api/v1/accounts", status_code: 401, response_time_ms: 12.1, anomaly_score: 0.150, is_anomalous: 0 }
    ],

    alerts: [
        {
            alert_id: "ALT-2026-901",
            app_id: "app_wealth_7730",
            severity: "HIGH",
            description: "Repeated customer consent revocation violation. Client attempting access without active authorization.",
            status: "NEW",
            ai_confidence: 0.94,
            timestamp: new Date(Date.now() - 1000 * 120).toISOString()
        }
    ],

    statusCodes: {
        "200": 34,
        "401": 2,
        "403": 3,
        "429": 1,
        "404": 0,
        "500": 0
    }
};

// =========================================================================
// Universal Gateway Fetch Wrapper (Auto Local vs In-Browser Sandbox)
// =========================================================================
async function gatewayFetch(url, options = {}) {
    // If we've already detected static/mock mode, dispatch directly to mock gateway
    if (isMockMode) {
        return mockGatewayDispatch(url, options);
    }

    try {
        const res = await fetch(url, options);
        // If 404 or backend unavailable, switch to mock mode
        if (res.status === 404 && url.startsWith("/api/")) {
            console.warn("Backend API route not found. Switching to In-Browser Sandbox mode.");
            setMockMode(true);
            return mockGatewayDispatch(url, options);
        }
        return res;
    } catch (err) {
        console.warn("Local gateway unreachable. Switching to In-Browser Sandbox mode.", err);
        setMockMode(true);
        return mockGatewayDispatch(url, options);
    }
}

function setMockMode(enabled) {
    isMockMode = enabled;
    const statusText = document.getElementById("gatewayStatusText");
    if (statusText) {
        if (enabled) {
            statusText.innerHTML = `Live Demo · <strong>In-Browser Sandbox</strong> (GitHub Pages)`;
        } else {
            statusText.innerHTML = `Gateway <strong>Live</strong> · Python Local (127.0.0.1:8000)`;
        }
    }
}

// In-Browser Mock Gateway Engine
function mockGatewayDispatch(url, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    const headers = options.headers || {};
    const parsedUrl = new URL(url, "https://securebank.local");
    const path = parsedUrl.pathname;
    const query = parsedUrl.searchParams;

    let body = {};
    if (options.body) {
        try { body = JSON.parse(options.body); } catch(e){}
    }

    // Helper: Build mock Response object
    const makeRes = (status, data) => {
        return {
            ok: status >= 200 && status < 300,
            status: status,
            statusText: status === 200 ? "OK" : status === 201 ? "Created" : "Error",
            json: async () => data
        };
    };

    // Latency simulation (instant for UI snappiness)
    const simulatedLatency = Math.floor(Math.random() * 25) + 15;

    // 1. App List: GET /api/v1/apps
    if (path === "/api/v1/apps" && method === "GET") {
        return makeRes(200, { apps: mockDb.apps });
    }

    // 2. Register App: POST /api/v1/apps
    if (path === "/api/v1/apps" && method === "POST") {
        const name = body.name || "Custom Partner App";
        const scopes = body.scopes || ["accounts:read", "balances:read"];
        const randId = Math.floor(1000 + Math.random() * 9000);
        const slug = name.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 8);
        const newApp = {
            client_id: `app_${slug}_${randId}`,
            client_secret: `sec_live_${Math.random().toString(36).substring(2, 14)}`,
            api_key: `sb_live_${slug}_${Math.random().toString(36).substring(2, 8)}`,
            name: name,
            developer_name: "Hackathon Evaluator",
            company_name: "Independent Developer",
            allowed_scopes: JSON.stringify(scopes),
            rate_limit: 60,
            is_active: 1
        };
        mockDb.apps.unshift(newApp);
        return makeRes(201, newApp);
    }

    // 3. Toggle App: POST /api/v1/apps/:id/toggle
    if (path.match(/^\/api\/v1\/apps\/([^\/]+)\/toggle$/) && method === "POST") {
        const clientId = path.split("/")[4];
        const app = mockDb.apps.find(a => a.client_id === clientId);
        if (app) {
            app.is_active = app.is_active === 1 ? 0 : 1;
            return makeRes(200, { success: true, is_active: app.is_active, client_id: clientId });
        }
        return makeRes(404, { error: "not_found", message: "Application not found" });
    }

    // 4. OAuth2 Token: POST /api/v1/oauth/token
    if (path === "/api/v1/oauth/token" && method === "POST") {
        const { client_id, client_secret, customer_id, scopes } = body;
        const app = mockDb.apps.find(a => a.client_id === client_id);
        if (!app || app.client_secret !== client_secret) {
            return makeRes(401, { error: "invalid_client", message: "Client credentials are not valid" });
        }
        if (app.is_active !== 1) {
            return makeRes(403, { error: "app_blocked", message: "Partner app is blocked or suspended by administrator" });
        }
        const token = `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIke2NsaWVudF9pZH0iLCJjdXN0b21lcl9pZCI6IiR7Y3VzdG9tZXJfaWR9Iiwic2NvcGVzIjpbIiR7KHNjb3BlcyB8fCBbXSkfam9pbignIiwiJyl9Il0sImV4cCI6JHtNYXRoLmZsb29yKERhdGUubm93KCkvMTAwMCkgKyAzNjAwfX0.simulated_valid_token`;
        return makeRes(200, {
            access_token: token,
            token_type: "Bearer",
            expires_in: 3600,
            scope: (scopes || []).join(" "),
            customer_id: customer_id || "CUST-1001"
        });
    }

    // 5. Consents List: GET /api/v1/consents
    if (path === "/api/v1/consents" && method === "GET") {
        return makeRes(200, { consents: mockDb.consents });
    }

    // 6. Grant Consent: POST /api/v1/consents
    if (path === "/api/v1/consents" && method === "POST") {
        const { customer_id, app_id, scopes } = body;
        const app = mockDb.apps.find(a => a.client_id === app_id);
        const cust = mockDb.customers.find(c => c.customer_id === customer_id);
        const newConsent = {
            consent_id: `CNS-${Math.floor(1000 + Math.random() * 9000)}-${cust ? cust.name.split(" ")[0].toUpperCase() : 'USER'}`,
            customer_id: customer_id,
            customer_name: cust ? cust.name : customer_id,
            app_id: app_id,
            app_name: app ? app.name : app_id,
            scopes: JSON.stringify(scopes || []),
            status: "ACTIVE",
            expires_at: new Date(Date.now() + 86400000 * 90).toISOString()
        };
        mockDb.consents.unshift(newConsent);
        return makeRes(201, { message: "Consent recorded", consent: newConsent });
    }

    // 7. Revoke Consent: POST /api/v1/consents/:id/revoke
    if (path.match(/^\/api\/v1\/consents\/([^\/]+)\/revoke$/) && method === "POST") {
        const consentId = path.split("/")[4];
        const c = mockDb.consents.find(item => item.consent_id === consentId);
        if (c) {
            c.status = "REVOKED";
            return makeRes(200, { message: `Customer consent '${consentId}' has been revoked. API access now blocked with 403 Forbidden.` });
        }
        return makeRes(404, { error: "not_found", message: "Consent not found" });
    }

    // 8. Open Banking Core APIs (Sandbox)
    // Extract client authorization & customer context
    let authAppId = null;
    let customerId = headers["X-Customer-Id"] || "CUST-1001";
    let grantedScopes = [];

    const authHeader = headers["Authorization"] || "";
    const apiKeyHeader = headers["X-Api-Key"] || "";

    if (authHeader.startsWith("Bearer ")) {
        // Parse simulated token
        const tokenStr = authHeader.replace("Bearer ", "").trim();
        if (tokenStr.includes("app_")) {
            const match = tokenStr.match(/sub":"(app_[^"]+)"/);
            if (match) authAppId = match[1];
        }
        if (!authAppId && mockDb.apps.length > 0) {
            authAppId = mockDb.apps[0].client_id;
        }
    } else if (apiKeyHeader) {
        const app = mockDb.apps.find(a => a.api_key === apiKeyHeader);
        if (app) {
            authAppId = app.client_id;
        } else {
            recordMockLog("UNAUTHORIZED", method, path, 401, 15, 0.22, 0);
            return makeRes(401, { error: "invalid_api_key", message: "Provided API key is not registered or valid" });
        }
    } else {
        recordMockLog("ANONYMOUS", method, path, 401, 10, 0.15, 0);
        return makeRes(401, { error: "unauthorized", message: "Missing authentication credentials. Supply 'Authorization: Bearer <token>' or 'X-Api-Key: <key>'" });
    }

    // Check App Active Status
    const targetApp = mockDb.apps.find(a => a.client_id === authAppId);
    if (targetApp && targetApp.is_active !== 1) {
        recordMockLog(authAppId, method, path, 403, 15, 0.45, 0);
        return makeRes(403, { error: "app_suspended", message: "Partner application is currently blocked or suspended by administrator" });
    }

    // Check Customer Consent for this App
    const consent = mockDb.consents.find(c => c.app_id === authAppId && c.customer_id === customerId);
    if (consent && consent.status === "REVOKED") {
        recordMockLog(authAppId, method, path, 403, 20, 0.88, 1);
        mockDb.alerts.unshift({
            alert_id: `ALT-${Math.floor(1000 + Math.random() * 9000)}`,
            app_id: authAppId,
            severity: "HIGH",
            description: `Blocked unauthorized request: Customer '${customerId}' has revoked consent for app '${authAppId}'.`,
            status: "NEW",
            ai_confidence: 0.96,
            timestamp: new Date().toISOString()
        });
        return makeRes(403, {
            error: "consent_revoked",
            message: `Customer ${customerId} has explicitly REVOKED data sharing consent for partner app ${authAppId}. Request denied.`,
            consent_id: consent.consent_id
        });
    }

    // Endpoint: GET /api/v1/accounts
    if (path === "/api/v1/accounts" && method === "GET") {
        const userAccounts = mockDb.accounts.filter(a => a.customer_id === customerId);
        recordMockLog(authAppId, method, path, 200, simulatedLatency, 0.035, 0);
        return makeRes(200, {
            customer_id: customerId,
            accounts: userAccounts,
            count: userAccounts.length
        });
    }

    // Endpoint: GET /api/v1/accounts/:id/balances
    if (path.match(/^\/api\/v1\/accounts\/([^\/]+)\/balances$/) && method === "GET") {
        const accId = path.split("/")[4];
        const acc = mockDb.accounts.find(a => a.account_id === accId);
        if (!acc) {
            recordMockLog(authAppId, method, path, 404, simulatedLatency, 0.12, 0);
            return makeRes(404, { error: "account_not_found", message: `Account '${accId}' does not exist` });
        }
        recordMockLog(authAppId, method, path, 200, simulatedLatency, 0.028, 0);
        return makeRes(200, {
            account_id: acc.account_id,
            currency: acc.currency,
            ledger_balance: acc.balance,
            available_balance: acc.available_balance,
            timestamp: new Date().toISOString()
        });
    }

    // Endpoint: GET /api/v1/accounts/:id/transactions
    if (path.match(/^\/api\/v1\/accounts\/([^\/]+)\/transactions$/) && method === "GET") {
        const accId = path.split("/")[4];
        const txs = mockDb.transactions.filter(t => t.account_id === accId || !accId);
        recordMockLog(authAppId, method, path, 200, simulatedLatency, 0.045, 0);
        return makeRes(200, {
            account_id: accId,
            transactions: txs.length > 0 ? txs : mockDb.transactions.slice(0, 5),
            total: txs.length
        });
    }

    // Endpoint: POST /api/v1/payments
    if (path === "/api/v1/payments" && method === "POST") {
        const { from_account_id, to_account_id, amount, currency, reference } = body;
        const sourceAcc = mockDb.accounts.find(a => a.account_id === from_account_id);
        const destAcc = mockDb.accounts.find(a => a.account_id === to_account_id);

        if (!sourceAcc) {
            recordMockLog(authAppId, method, path, 400, simulatedLatency, 0.18, 0);
            return makeRes(400, { error: "invalid_account", message: "Source account not found" });
        }

        const amt = parseFloat(amount) || 0;
        if (sourceAcc.available_balance < amt) {
            recordMockLog(authAppId, method, path, 400, simulatedLatency, 0.25, 0);
            return makeRes(400, { error: "insufficient_funds", message: "Available balance is less than transfer amount" });
        }

        // Deduct balance and credit target
        sourceAcc.available_balance = parseFloat((sourceAcc.available_balance - amt).toFixed(2));
        sourceAcc.balance = parseFloat((sourceAcc.balance - amt).toFixed(2));
        if (destAcc) {
            destAcc.available_balance = parseFloat((destAcc.available_balance + amt).toFixed(2));
            destAcc.balance = parseFloat((destAcc.balance + amt).toFixed(2));
        }

        const paymentTx = {
            payment_id: `PMT-2026-${Math.floor(1000 + Math.random() * 9000)}`,
            from_account_id: from_account_id,
            to_account_id: to_account_id,
            amount: amt,
            currency: currency || "USD",
            reference: reference || "Open Banking Payment",
            status: "SETTLED",
            settled_at: new Date().toISOString()
        };

        mockDb.transactions.unshift({
            transaction_id: `TXN-${paymentTx.payment_id}`,
            account_id: from_account_id,
            timestamp: paymentTx.settled_at,
            type: "DEBIT",
            amount: amt,
            description: `Payment to ${to_account_id}: ${paymentTx.reference}`,
            category: "Transfer",
            status: "SETTLED",
            reference: paymentTx.payment_id,
            counterparty: to_account_id
        });

        recordMockLog(authAppId, method, path, 201, simulatedLatency + 20, 0.082, 0);
        return makeRes(201, paymentTx);
    }

    // 9. Monitoring & Telemetry
    if (path === "/api/v1/monitoring/metrics" && method === "GET") {
        const total = mockDb.logs.length;
        const anomCount = mockDb.logs.filter(l => l.is_anomalous === 1).length;
        const activeApps = mockDb.apps.filter(a => a.is_active === 1).length;
        const avgLat = mockDb.logs.length > 0
            ? Math.round(mockDb.logs.reduce((acc, l) => acc + l.response_time_ms, 0) / mockDb.logs.length)
            : 32;
        const errorCount = mockDb.logs.filter(l => l.status_code >= 400).length;
        const errRate = total > 0 ? ((errorCount / total) * 100).toFixed(1) : "0.0";

        return makeRes(200, {
            total_requests: total + 42,
            active_partner_apps: activeApps,
            anomalies_detected: anomCount + mockDb.alerts.length,
            avg_latency_ms: avgLat,
            error_rate_pct: errRate,
            status_code_breakdown: mockDb.statusCodes
        });
    }

    if (path === "/api/v1/monitoring/logs" && method === "GET") {
        return makeRes(200, { logs: mockDb.logs });
    }

    if (path === "/api/v1/monitoring/alerts" && method === "GET") {
        return makeRes(200, { alerts: mockDb.alerts });
    }

    if (path.match(/^\/api\/v1\/monitoring\/alerts\/([^\/]+)\/resolve$/) && method === "POST") {
        const alertId = path.split("/")[5];
        const a = mockDb.alerts.find(alt => alt.alert_id === alertId);
        if (a) a.status = "RESOLVED";
        return makeRes(200, { message: `Alert ${alertId} resolved` });
    }

    if (path.match(/^\/api\/v1\/monitoring\/alerts\/([^\/]+)\/suspend-app$/) && method === "POST") {
        const alertId = path.split("/")[5];
        const a = mockDb.alerts.find(alt => alt.alert_id === alertId);
        if (a) {
            const app = mockDb.apps.find(item => item.client_id === a.app_id);
            if (app) app.is_active = 0;
            a.status = "RESOLVED";
            return makeRes(200, { message: `Partner app ${a.app_id} suspended and alert marked resolved.` });
        }
        return makeRes(404, { error: "not_found", message: "Alert not found" });
    }

    // 10. Attack Simulator: POST /api/v1/simulate/traffic
    if (path === "/api/v1/simulate/traffic" && method === "POST") {
        const scenario = body.scenario || "normal_traffic";
        let simulatedCount = 0;
        let anomCount = 0;

        if (scenario === "traffic_burst") {
            simulatedCount = 15;
            anomCount = 12;
            for (let i = 0; i < 15; i++) {
                const isErr = i > 8;
                const status = isErr ? 429 : 200;
                const score = isErr ? 0.92 : 0.45;
                recordMockLog("app_wealth_7730", "GET", "/api/v1/accounts", status, 120 + i * 15, score, isErr ? 1 : 0);
            }
            mockDb.alerts.unshift({
                alert_id: `ALT-BURST-${Math.floor(1000 + Math.random() * 9000)}`,
                app_id: "app_wealth_7730",
                severity: "CRITICAL",
                description: "DDoS Traffic Spike detected: Request rate exceeded 15 req/sec with elevated latency deviations.",
                status: "NEW",
                ai_confidence: 0.98,
                timestamp: new Date().toISOString()
            });
        } else if (scenario === "credential_stuffing") {
            simulatedCount = 10;
            anomCount = 9;
            for (let i = 0; i < 10; i++) {
                recordMockLog("UNKNOWN_CLIENT", "POST", "/api/v1/oauth/token", 401, 24, 0.89, 1);
            }
            mockDb.alerts.unshift({
                alert_id: `ALT-AUTH-${Math.floor(1000 + Math.random() * 9000)}`,
                app_id: "ANONYMOUS",
                severity: "HIGH",
                description: "Credential stuffing attack detected: 10 failed HMAC token verifications in sliding 60s window.",
                status: "NEW",
                ai_confidence: 0.95,
                timestamp: new Date().toISOString()
            });
        } else if (scenario === "scope_violation") {
            simulatedCount = 8;
            anomCount = 7;
            for (let i = 0; i < 8; i++) {
                recordMockLog("app_finpulse_9281", "POST", "/api/v1/payments", 403, 31, 0.86, 1);
            }
            mockDb.alerts.unshift({
                alert_id: `ALT-SCOPE-${Math.floor(1000 + Math.random() * 9000)}`,
                app_id: "app_finpulse_9281",
                severity: "HIGH",
                description: "Repeated unauthorized scope escalation: Partner app attempting 'payments:create' without granted scope.",
                status: "NEW",
                ai_confidence: 0.91,
                timestamp: new Date().toISOString()
            });
        } else {
            // normal traffic
            simulatedCount = 6;
            anomCount = 0;
            for (let i = 0; i < 6; i++) {
                recordMockLog("app_quickinv_4412", "GET", "/api/v1/accounts/ACC-US-8903/balances", 200, 22 + i * 2, 0.021, 0);
            }
        }

        return makeRes(200, {
            scenario: scenario,
            simulated_requests: simulatedCount,
            anomalies_detected: anomCount,
            message: `Simulation '${scenario}' executed successfully.`
        });
    }

    return makeRes(404, { error: "not_found", message: `Resource '${path}' not found` });
}

function recordMockLog(appId, method, endpoint, status, latency, anomScore, isAnom) {
    mockDb.logs.unshift({
        timestamp: new Date().toISOString(),
        app_id: appId,
        method: method,
        endpoint: endpoint,
        status_code: status,
        response_time_ms: Math.round(latency),
        anomaly_score: anomScore,
        is_anomalous: isAnom
    });

    if (mockDb.logs.length > 50) {
        mockDb.logs.pop();
    }

    const sStr = String(status);
    if (mockDb.statusCodes[sStr] !== undefined) {
        mockDb.statusCodes[sStr]++;
    } else {
        mockDb.statusCodes["Other"] = (mockDb.statusCodes["Other"] || 0) + 1;
    }
}

// =========================================================================
// Initialization & Navigation
// =========================================================================
document.addEventListener("DOMContentLoaded", async () => {
    // Proactively detect environment
    const isGithubPages = window.location.hostname.includes("github.io") || window.location.protocol === "file:";
    if (isGithubPages) {
        setMockMode(true);
    }

    setupTabNavigation();
    setupForms();

    await loadPartnerApps();
    await loadConsents();
    await loadMonitoringData();

    // Polling for metrics every 5s
    pollTimer = setInterval(() => {
        loadMetrics();
    }, 5000);
});

function switchTab(tabId) {
    document.querySelectorAll(".nav-tab").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.tab === tabId);
    });
    document.querySelectorAll(".tab-content").forEach(tab => {
        tab.classList.toggle("active", tab.id === `tab-${tabId}`);
    });

    if (tabId === "monitoring") {
        loadMonitoringData();
    } else if (tabId === "consent") {
        loadConsents();
    } else if (tabId === "devportal") {
        loadPartnerApps();
    }
}

function setupTabNavigation() {
    document.querySelectorAll(".nav-tab").forEach(btn => {
        btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });
}

// =========================================================================
// TAB 2: Developer Portal & App Management
// =========================================================================
async function loadPartnerApps() {
    try {
        const res = await gatewayFetch("/api/v1/apps");
        const data = await res.json();
        registeredApps = data.apps || [];
        renderAppsList();
        populateSandboxAppSelect();
        populateConsentAppSelect();
    } catch (err) {
        console.error("Error loading apps:", err);
    }
}

function renderAppsList() {
    const container = document.getElementById("appsListContainer");
    if (!container) return;

    if (registeredApps.length === 0) {
        container.innerHTML = `<div class="empty-state">No partner applications registered yet.</div>`;
        return;
    }

    container.innerHTML = registeredApps.map(app => {
        let scopes = [];
        try { scopes = JSON.parse(app.allowed_scopes); } catch(e){}

        const isActive = app.is_active === 1;
        const statusBadge = isActive
            ? `<span class="badge badge-emerald">ACTIVE</span>`
            : `<span class="badge badge-crimson">SUSPENDED / BLOCKED</span>`;

        return `
            <div class="app-item-card">
                <div class="app-item-header">
                    <div>
                        <span class="app-item-name">${escapeHtml(app.name || app.app_name)}</span>
                        ${statusBadge}
                    </div>
                    <button class="btn btn-sm ${isActive ? 'btn-secondary' : 'btn-emerald'}" onclick="toggleAppStatus('${app.client_id}')">
                        ${isActive ? 'Block App' : 'Activate App'}
                    </button>
                </div>
                <div class="app-meta-grid">
                    <div class="app-meta-box">
                        <span class="app-meta-label">Client ID</span>
                        <code class="app-meta-val code-font">${app.client_id}</code>
                    </div>
                    <div class="app-meta-box">
                        <span class="app-meta-label">API Key</span>
                        <code class="app-meta-val code-font">${app.api_key}</code>
                    </div>
                    <div class="app-meta-box">
                        <span class="app-meta-label">Client Secret</span>
                        <code class="app-meta-val code-font">${app.client_secret}</code>
                    </div>
                    <div class="app-meta-box">
                        <span class="app-meta-label">Rate Limit</span>
                        <span class="app-meta-val">${app.rate_limit} req/min</span>
                    </div>
                </div>
                ${app.developer_name ? `<div class="text-xs text-dim mt-1">Developer: <strong class="text-main">${escapeHtml(app.developer_name)}</strong> · ${escapeHtml(app.company_name || '')}</div>` : ''}
                <div class="mt-1">
                    <span class="text-dim text-xs">Granted Scopes: </span>
                    ${scopes.map(s => `<span class="badge badge-blue code-font" style="font-size:0.65rem">${s}</span>`).join(" ")}
                </div>
            </div>
        `;
    }).join("");
}

async function toggleAppStatus(clientId) {
    try {
        const res = await gatewayFetch(`/api/v1/apps/${clientId}/toggle`, { method: "POST" });
        await res.json();
        await loadPartnerApps();
        await loadMetrics();
    } catch (e) {
        alert("Failed to toggle app status: " + e.message);
    }
}

function setupForms() {
    // App Registration
    const appForm = document.getElementById("appRegisterForm");
    if (appForm) {
        appForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const name = document.getElementById("appNameInput").value.trim();
            const checkedBoxes = document.querySelectorAll('input[name="scopes"]:checked');
            const scopes = Array.from(checkedBoxes).map(cb => cb.value);

            try {
                const res = await gatewayFetch("/api/v1/apps", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name, scopes })
                });
                const data = await res.json();
                if (res.ok) {
                    appForm.reset();
                    alert(`Application '${data.name}' registered successfully! Credentials generated.`);
                    await loadPartnerApps();
                } else {
                    alert(`Error: ${data.message || data.error}`);
                }
            } catch (err) {
                alert("Failed to register app: " + err.message);
            }
        });
    }

    // Grant Consent Form
    const consentForm = document.getElementById("grantConsentForm");
    if (consentForm) {
        consentForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const customer_id = document.getElementById("consentCustomerSelect").value;
            const app_id = document.getElementById("consentAppSelect").value;
            const checkedBoxes = document.querySelectorAll('input[name="cScopes"]:checked');
            const scopes = Array.from(checkedBoxes).map(cb => cb.value);

            if (scopes.length === 0) {
                alert("Please select at least one permission scope to grant.");
                return;
            }

            try {
                const res = await gatewayFetch("/api/v1/consents", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ customer_id, app_id, scopes })
                });
                const data = await res.json();
                if (res.ok) {
                    alert("Customer consent recorded successfully!");
                    await loadConsents();
                    await loadMetrics();
                } else {
                    alert(`Error: ${data.message || data.error}`);
                }
            } catch (err) {
                alert("Failed to grant consent: " + err.message);
            }
        });
    }
}

function populateConsentAppSelect() {
    const sel = document.getElementById("consentAppSelect");
    if (!sel) return;
    sel.innerHTML = registeredApps.map(a => `<option value="${a.client_id}">${escapeHtml(a.name || a.app_name)} (${a.client_id})</option>`).join("");
}

// =========================================================================
// TAB 3: API Sandbox Console
// =========================================================================
function populateSandboxAppSelect() {
    const sel = document.getElementById("sandboxAppSelect");
    if (!sel) return;
    sel.innerHTML = registeredApps.map((a, idx) => `
        <option value="${a.client_id}" ${idx === 0 ? 'selected' : ''}>
            ${escapeHtml(a.name || a.app_name)} · ${a.client_id}
        </option>
    `).join("");

    if (registeredApps.length > 0) {
        onSandboxAppChange();
    }
}

function onSandboxAppChange() {
    const sel = document.getElementById("sandboxAppSelect");
    if (!sel) return;
    const app = registeredApps.find(a => a.client_id === sel.value);
    if (!app) return;

    const apiKeyInput = document.getElementById("sandboxApiKeyInput");
    if (apiKeyInput) {
        apiKeyInput.value = app.api_key;
    }
    generateTokenFromSelectedApp();
}

async function generateTokenFromSelectedApp() {
    const sel = document.getElementById("sandboxAppSelect");
    const custSel = document.getElementById("sandboxCustomerSelect");
    if (!sel || !custSel) return;

    const app = registeredApps.find(a => a.client_id === sel.value);
    if (!app) return;

    let scopes = [];
    try { scopes = JSON.parse(app.allowed_scopes); } catch(e){}

    try {
        const res = await gatewayFetch("/api/v1/oauth/token", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                client_id: app.client_id,
                client_secret: app.client_secret,
                customer_id: custSel.value,
                scopes: scopes
            })
        });
        const data = await res.json();
        if (data.access_token) {
            document.getElementById("sandboxTokenInput").value = data.access_token;
        }
    } catch(e) {
        console.error("Token error:", e);
    }
}

function toggleAuthMode() {
    const mode = document.querySelector('input[name="authMode"]:checked').value;
    const tokenGroup = document.getElementById("tokenFieldGroup");
    const apiKeyGroup = document.getElementById("apiKeyFieldGroup");

    if (mode === "token") {
        tokenGroup.style.display = "block";
        apiKeyGroup.style.display = "none";
    } else {
        tokenGroup.style.display = "none";
        apiKeyGroup.style.display = "block";
    }
}

function setEndpointPreset(preset) {
    document.querySelectorAll(".btn-preset").forEach(b => b.classList.remove("active"));
    const methodSel = document.getElementById("requestMethodSelect");
    const urlInput = document.getElementById("requestUrlInput");
    const bodyPanel = document.getElementById("requestBodyPanel");

    if (preset === "get_accounts") {
        methodSel.value = "GET";
        urlInput.value = "/api/v1/accounts";
        bodyPanel.style.display = "none";
    } else if (preset === "get_balances") {
        methodSel.value = "GET";
        urlInput.value = "/api/v1/accounts/ACC-US-8901/balances";
        bodyPanel.style.display = "none";
    } else if (preset === "get_transactions") {
        methodSel.value = "GET";
        urlInput.value = "/api/v1/accounts/ACC-US-8901/transactions?limit=10";
        bodyPanel.style.display = "none";
    } else if (preset === "post_payments") {
        methodSel.value = "POST";
        urlInput.value = "/api/v1/payments";
        bodyPanel.style.display = "block";
    } else if (preset === "get_consents") {
        methodSel.value = "GET";
        urlInput.value = "/api/v1/consents";
        bodyPanel.style.display = "none";
    }

    if (window.event && window.event.target) {
        window.event.target.classList.add("active");
    }
}

async function executeSandboxRequest() {
    const method = document.getElementById("requestMethodSelect").value;
    const url = document.getElementById("requestUrlInput").value;
    const authMode = document.querySelector('input[name="authMode"]:checked').value;
    const token = document.getElementById("sandboxTokenInput").value.trim();
    const apiKey = document.getElementById("sandboxApiKeyInput").value.trim();
    const customerId = document.getElementById("sandboxCustomerSelect").value;

    const headers = {
        "Content-Type": "application/json"
    };

    if (authMode === "token" && token) {
        headers["Authorization"] = `Bearer ${token}`;
    } else if (authMode === "apikey" && apiKey) {
        headers["X-Api-Key"] = apiKey;
        headers["X-Customer-Id"] = customerId;
    }

    const options = {
        method: method,
        headers: headers
    };

    if (method === "POST") {
        const bodyContent = document.getElementById("requestBodyJson").value;
        try {
            JSON.parse(bodyContent);
            options.body = bodyContent;
        } catch(e) {
            alert("Invalid JSON format in Request Body!");
            return;
        }
    }

    const statusBadge = document.getElementById("responseStatusBadge");
    const latencyBadge = document.getElementById("responseLatencyBadge");
    const jsonViewer = document.getElementById("responseJsonViewer");

    statusBadge.className = "badge badge-gray";
    statusBadge.textContent = "Sending...";
    latencyBadge.textContent = "-- ms";

    const startTime = performance.now();

    try {
        const res = await gatewayFetch(url, options);
        const duration = Math.round(performance.now() - startTime);
        const data = await res.json();

        latencyBadge.textContent = `${duration} ms`;

        if (res.status === 200 || res.status === 201) {
            statusBadge.className = "badge badge-emerald";
            statusBadge.textContent = `${res.status} OK`;
        } else if (res.status === 401) {
            statusBadge.className = "badge badge-amber";
            statusBadge.textContent = `${res.status} UNAUTHORIZED`;
        } else if (res.status === 403) {
            statusBadge.className = "badge badge-crimson";
            statusBadge.textContent = `${res.status} FORBIDDEN (Consent/Scope Denied)`;
        } else if (res.status === 429) {
            statusBadge.className = "badge badge-purple";
            statusBadge.textContent = `${res.status} RATE LIMITED`;
        } else {
            statusBadge.className = "badge badge-crimson";
            statusBadge.textContent = `${res.status} ERROR`;
        }

        jsonViewer.innerHTML = `<code>${escapeHtml(JSON.stringify(data, null, 2))}</code>`;
        loadMetrics();
    } catch(err) {
        statusBadge.className = "badge badge-crimson";
        statusBadge.textContent = "CONNECTION ERROR";
        jsonViewer.innerHTML = `<code>${escapeHtml(JSON.stringify({ error: err.message }, null, 2))}</code>`;
    }
}

function copyResponse() {
    const text = document.getElementById("responseJsonViewer").textContent;
    navigator.clipboard.writeText(text).then(() => {
        alert("Response copied to clipboard!");
    });
}

// =========================================================================
// TAB 4: Customer Consent Management
// =========================================================================
async function loadConsents() {
    try {
        const res = await gatewayFetch("/api/v1/consents");
        const data = await res.json();
        renderConsentsTable(data.consents || []);
    } catch(e) {
        console.error("Error loading consents:", e);
    }
}

function renderConsentsTable(consents) {
    const container = document.getElementById("consentsTableContainer");
    if (!container) return;

    if (consents.length === 0) {
        container.innerHTML = `<div class="empty-state">No consent records found.</div>`;
        return;
    }

    container.innerHTML = `
        <table class="styled-table">
            <thead>
                <tr>
                    <th>Consent ID</th>
                    <th>Customer</th>
                    <th>Authorized Partner App</th>
                    <th>Granted Permissions</th>
                    <th>Expires</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                ${consents.map(c => {
                    let scopes = [];
                    try { scopes = JSON.parse(c.scopes); } catch(e){}

                    const isRevoked = c.status === "REVOKED";
                    const statusBadge = isRevoked
                        ? `<span class="badge badge-crimson">REVOKED</span>`
                        : `<span class="badge badge-emerald">ACTIVE</span>`;

                    const actionBtn = isRevoked
                        ? `<span class="text-dim text-xs">Revoked</span>`
                        : `<button class="btn btn-sm btn-secondary text-crimson" onclick="revokeConsent('${c.consent_id}')">Revoke Consent</button>`;

                    const expFormatted = c.expires_at ? c.expires_at.split("T")[0] : "--";

                    return `
                        <tr>
                            <td><code class="code-font">${c.consent_id}</code></td>
                            <td><strong>${escapeHtml(c.customer_name || c.customer_id)}</strong><br><span class="text-dim text-xs">${c.customer_id}</span></td>
                            <td><strong>${escapeHtml(c.app_name || c.app_id)}</strong></td>
                            <td>
                                ${scopes.map(s => `<span class="badge badge-blue" style="font-size:0.65rem">${s}</span>`).join(" ")}
                            </td>
                            <td>${expFormatted}</td>
                            <td>${statusBadge}</td>
                            <td>${actionBtn}</td>
                        </tr>
                    `;
                }).join("")}
            </tbody>
        </table>
    `;
}

async function revokeConsent(consentId) {
    if (!confirm(`Are you sure you want to revoke consent '${consentId}'? The partner app will immediately receive 403 Forbidden.`)) {
        return;
    }

    try {
        const res = await gatewayFetch(`/api/v1/consents/${consentId}/revoke`, { method: "POST" });
        const data = await res.json();
        alert(data.message || "Consent revoked");
        await loadConsents();
        await loadMetrics();
    } catch(e) {
        alert("Failed to revoke consent: " + e.message);
    }
}

// =========================================================================
// TAB 5: AI Monitoring & Threat Detection
// =========================================================================
async function loadMonitoringData() {
    await loadMetrics();
    await loadAlerts();
    await loadAuditLogs();
}

async function loadMetrics() {
    try {
        const res = await gatewayFetch("/api/v1/monitoring/metrics");
        const m = await res.json();

        const totalEl = document.getElementById("metricTotalCalls");
        if (totalEl) totalEl.textContent = m.total_requests.toLocaleString();

        const appsEl = document.getElementById("metricActiveApps");
        if (appsEl) appsEl.textContent = m.active_partner_apps;

        const anomEl = document.getElementById("metricAnomalies");
        if (anomEl) anomEl.textContent = m.anomalies_detected;

        const latEl = document.getElementById("metricAvgLatency");
        if (latEl) latEl.textContent = `${m.avg_latency_ms} ms`;

        const errEl = document.getElementById("metricErrorRate");
        if (errEl) errEl.textContent = `${m.error_rate_pct}%`;

        // Threat dot indicator in header
        const threatDot = document.getElementById("headerThreatDot");
        if (threatDot) {
            threatDot.style.display = m.anomalies_detected > 0 ? "inline-block" : "none";
        }

        renderStatusCodeChart(m.status_code_breakdown);
    } catch(e) {
        console.error("Error loading metrics:", e);
    }
}

function renderStatusCodeChart(breakdown) {
    const ctx = document.getElementById("statusCodeChart");
    if (!ctx) return;

    const labels = ["200 OK", "401 Unauthorized", "403 Forbidden", "429 Rate Limit", "Other"];
    const counts = [
        breakdown["200"] || 0,
        breakdown["401"] || 0,
        breakdown["403"] || 0,
        breakdown["429"] || 0,
        (breakdown["404"] || 0) + (breakdown["500"] || 0) + (breakdown["Other"] || 0)
    ];

    if (chartInstance) {
        chartInstance.data.datasets[0].data = counts;
        chartInstance.update();
        return;
    }

    chartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: counts,
                backgroundColor: [
                    '#10b981', // green 200
                    '#f59e0b', // amber 401
                    '#ef4444', // red 403
                    '#8b5cf6', // purple 429
                    '#64748b'  // gray
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94a3b8', font: { family: 'Plus Jakarta Sans', size: 11 } }
                }
            },
            cutout: '70%'
        }
    });
}

async function loadAlerts() {
    try {
        const res = await gatewayFetch("/api/v1/monitoring/alerts");
        const data = await res.json();
        renderAlerts(data.alerts || []);
    } catch(e) {
        console.error("Error loading alerts:", e);
    }
}

function renderAlerts(alerts) {
    const container = document.getElementById("alertsContainer");
    if (!container) return;

    if (alerts.length === 0) {
        container.innerHTML = `<div class="empty-state text-dim text-sm" style="padding:1.5rem; text-align:center;">No active security alerts. AI monitoring baseline normal.</div>`;
        return;
    }

    container.innerHTML = alerts.map(a => {
        const isResolved = a.status === "RESOLVED";
        const sevClass = a.severity || "MEDIUM";

        return `
            <div class="alert-item ${sevClass}">
                <div class="alert-item-header">
                    <div>
                        <span class="badge ${sevClass === 'CRITICAL' ? 'badge-crimson' : sevClass === 'HIGH' ? 'badge-amber' : 'badge-blue'}">${a.severity}</span>
                        <code class="code-font text-xs text-dim" style="margin-left:0.5rem">${a.alert_id}</code>
                    </div>
                    <div>
                        ${isResolved
                            ? `<span class="badge badge-emerald">RESOLVED</span>`
                            : `
                                <button class="btn btn-sm btn-secondary" onclick="resolveAlert('${a.alert_id}')">Acknowledge</button>
                                <button class="btn btn-sm btn-crimson-sm" style="margin-left:0.35rem" onclick="suspendAppFromAlert('${a.alert_id}', '${a.app_id}')">⛔ Suspend Key</button>
                              `
                        }
                    </div>
                </div>
                <div class="alert-desc">${escapeHtml(a.description)}</div>
                <div class="flex-between text-xs text-dim mt-1">
                    <span>Target App: <code>${a.app_id}</code></span>
                    <span>AI Confidence: <strong>${Math.round(a.ai_confidence * 100)}%</strong></span>
                </div>
            </div>
        `;
    }).join("");
}

async function resolveAlert(alertId) {
    try {
        await gatewayFetch(`/api/v1/monitoring/alerts/${alertId}/resolve`, { method: "POST" });
        await loadAlerts();
        await loadMetrics();
    } catch(e) {
        console.error("Error resolving alert:", e);
    }
}

async function suspendAppFromAlert(alertId, appId) {
    if (!confirm(`Suspend partner app '${appId}' immediately? This will block all subsequent requests at Auth & Consent Checks.`)) {
        return;
    }
    try {
        const res = await gatewayFetch(`/api/v1/monitoring/alerts/${alertId}/suspend-app`, { method: "POST" });
        const data = await res.json();
        alert(data.message || `App ${appId} suspended.`);
        await loadAlerts();
        await loadPartnerApps();
        await loadMetrics();
    } catch(e) {
        alert("Failed to suspend app: " + e.message);
    }
}

async function loadAuditLogs() {
    try {
        const res = await gatewayFetch("/api/v1/monitoring/logs?limit=25");
        const data = await res.json();
        renderAuditLogs(data.logs || []);
    } catch(e) {
        console.error("Error loading audit logs:", e);
    }
}

function renderAuditLogs(logs) {
    const tbody = document.getElementById("auditLogsBody");
    if (!tbody) return;

    if (logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-dim">No audit logs recorded yet.</td></tr>`;
        return;
    }

    tbody.innerHTML = logs.map(l => {
        const isAnom = l.is_anomalous === 1;
        const anomClass = isAnom ? "badge-crimson" : "badge-emerald";
        const anomLabel = isAnom ? "ANOMALOUS" : "NORMAL";

        let statusClass = "badge-emerald";
        if (l.status_code === 401) statusClass = "badge-amber";
        if (l.status_code === 403) statusClass = "badge-crimson";
        if (l.status_code === 429) statusClass = "badge-purple";
        if (l.status_code >= 500) statusClass = "badge-crimson";

        const timeStr = l.timestamp.includes("T") ? l.timestamp.split("T")[1].slice(0, 8) : l.timestamp;

        return `
            <tr>
                <td><code class="code-font text-dim">${timeStr}</code></td>
                <td><code class="code-font">${l.app_id || 'ANONYMOUS'}</code></td>
                <td><strong>${l.method}</strong></td>
                <td><code class="code-font">${l.endpoint}</code></td>
                <td><span class="badge ${statusClass}">${l.status_code}</span></td>
                <td>${l.response_time_ms} ms</td>
                <td><span class="code-font">${l.anomaly_score}</span></td>
                <td><span class="badge ${anomClass}">${anomLabel}</span></td>
            </tr>
        `;
    }).join("");
}

async function triggerSimulation(scenario) {
    const statusPill = document.getElementById("simulatorRunningStatus");
    if (statusPill) {
        statusPill.className = "badge badge-amber";
        statusPill.textContent = `Simulating ${scenario}...`;
    }

    try {
        const res = await gatewayFetch("/api/v1/simulate/traffic", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ scenario })
        });
        const data = await res.json();

        if (statusPill) {
            statusPill.className = "badge badge-emerald";
            statusPill.textContent = `Completed (${data.simulated_requests} calls, ${data.anomalies_detected} anomalies)`;
        }

        // Refresh all monitoring views
        await loadMetrics();
        await loadAlerts();
        await loadAuditLogs();

        setTimeout(() => {
            if (statusPill) {
                statusPill.className = "badge badge-gray";
                statusPill.textContent = "Idle";
            }
        }, 4000);
    } catch(e) {
        if (statusPill) {
            statusPill.className = "badge badge-crimson";
            statusPill.textContent = "Simulation Failed";
        }
    }
}

// Helpers
function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
