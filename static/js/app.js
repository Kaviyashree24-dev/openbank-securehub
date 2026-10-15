/**
 * SecureBank Connect - Frontend Application Logic
 */

let registeredApps = [];
let chartInstance = null;
let pollTimer = null;

// =========================================================================
// Initialization & Navigation
// =========================================================================
document.addEventListener("DOMContentLoaded", () => {
    setupTabNavigation();
    setupForms();
    loadPartnerApps();
    loadConsents();
    loadMonitoringData();

    // Polling for metrics every 4s
    pollTimer = setInterval(() => {
        loadMetrics();
    }, 4000);
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
        const res = await fetch("/api/v1/apps");
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
                        <span class="app-item-name">${escapeHtml(app.name)}</span>
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
        const res = await fetch(`/api/v1/apps/${clientId}/toggle`, { method: "POST" });
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
                const res = await fetch("/api/v1/apps", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name, scopes })
                });
                const data = await res.json();
                if (res.ok) {
                    appForm.reset();
                    alert(`Application '${data.name}' registered successfully!`);
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
                const res = await fetch("/api/v1/consents", {
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
    sel.innerHTML = registeredApps.map(a => `<option value="${a.client_id}">${a.name} (${a.client_id})</option>`).join("");
}

// =========================================================================
// TAB 3: API Sandbox Console
// =========================================================================
function populateSandboxAppSelect() {
    const sel = document.getElementById("sandboxAppSelect");
    if (!sel) return;
    sel.innerHTML = registeredApps.map((a, idx) => `
        <option value="${a.client_id}" ${idx === 0 ? 'selected' : ''}>
            ${a.name} · ${a.client_id}
        </option>
    `).join("");

    if (registeredApps.length > 0) {
        onSandboxAppChange();
    }
}

function onSandboxAppChange() {
    const sel = document.getElementById("sandboxAppSelect");
    const app = registeredApps.find(a => a.client_id === sel.value);
    if (!app) return;

    document.getElementById("sandboxApiKeyInput").value = app.api_key;
    // Generate initial token for ease of testing
    generateTokenFromSelectedApp();
}

async function generateTokenFromSelectedApp() {
    const sel = document.getElementById("sandboxAppSelect");
    const custSel = document.getElementById("sandboxCustomerSelect");
    const app = registeredApps.find(a => a.client_id === sel.value);
    if (!app) return;

    let scopes = [];
    try { scopes = JSON.parse(app.allowed_scopes); } catch(e){}

    try {
        const res = await fetch("/api/v1/oauth/token", {
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

    event.target.classList.add("active");
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
            JSON.parse(bodyContent); // validate JSON
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
        const res = await fetch(url, options);
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
        
        // Refresh metrics quietly in the background
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
        const res = await fetch("/api/v1/consents");
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
        const res = await fetch(`/api/v1/consents/${consentId}/revoke`, { method: "POST" });
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
        const res = await fetch("/api/v1/monitoring/metrics");
        const m = await res.json();

        document.getElementById("metricTotalCalls").textContent = m.total_requests.toLocaleString();
        document.getElementById("metricActiveApps").textContent = m.active_partner_apps;
        document.getElementById("metricAnomalies").textContent = m.anomalies_detected;
        document.getElementById("metricAvgLatency").textContent = `${m.avg_latency_ms} ms`;
        document.getElementById("metricErrorRate").textContent = `${m.error_rate_pct}%`;

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
        (breakdown["404"] || 0) + (breakdown["500"] || 0)
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
        const res = await fetch("/api/v1/monitoring/alerts");
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
                            : `<button class="btn btn-sm btn-secondary" onclick="resolveAlert('${a.alert_id}')">Acknowledge</button>`
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
        await fetch(`/api/v1/monitoring/alerts/${alertId}/resolve`, { method: "POST" });
        await loadAlerts();
        await loadMetrics();
    } catch(e) {
        console.error("Error resolving alert:", e);
    }
}

async function loadAuditLogs() {
    try {
        const res = await fetch("/api/v1/monitoring/logs?limit=25");
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

        const timeStr = l.timestamp.split("T")[1]?.slice(0, 8) || l.timestamp;

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
    statusPill.className = "badge badge-amber";
    statusPill.textContent = `Simulating ${scenario}...`;

    try {
        const res = await fetch("/api/v1/simulate/traffic", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ scenario })
        });
        const data = await res.json();

        statusPill.className = "badge badge-emerald";
        statusPill.textContent = `Completed (${data.simulated_requests} calls, ${data.anomalies_detected} anomalies)`;

        // Refresh all monitoring views
        await loadMetrics();
        await loadAlerts();
        await loadAuditLogs();

        setTimeout(() => {
            statusPill.className = "badge badge-gray";
            statusPill.textContent = "Idle";
        }, 4000);
    } catch(e) {
        statusPill.className = "badge badge-crimson";
        statusPill.textContent = "Simulation Failed";
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
