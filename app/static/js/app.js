// MILICONFIG Client Application Engine
let currentUsers = [];

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function showToast(message, type = "success") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = "toast";
  if (type === "error") {
    toast.style.borderLeftColor = "var(--danger)";
  } else if (type === "warn") {
    toast.style.borderLeftColor = "var(--warning)";
  }
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

function openModal(id) {
  const m = document.getElementById(id);
  if (m) m.style.display = "flex";
}

function closeModal(id) {
  const m = document.getElementById(id);
  if (m) m.style.display = "none";
}

// Navigation Tabs
document.querySelectorAll(".nav-item").forEach(item => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach(i => i.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(p => p.style.display = "none");
    item.classList.add("active");
    const target = item.getAttribute("data-tab");
    const pane = document.getElementById(`tab-${target}`);
    if (pane) pane.style.display = "block";
    document.getElementById("section-title").textContent = item.textContent.replace(/^[^\w\s]+/, "").trim();

    // Close mobile drawer on item click
    document.getElementById("sidebar").classList.remove("open");

    // Load data for selected tab
    if (target === "dashboard") loadDashboard();
    else if (target === "users") loadUsers();
    else if (target === "nodes") loadNodes();
    else if (target === "subscriptions") loadSubscriptions();
    else if (target === "shadowsocks") loadShadowSocks();
    else if (target === "proxyip") loadProxyIPs();
    else if (target === "dns") loadDNS();
    else if (target === "routing") loadRouting();
    else if (target === "traffic") loadTraffic();
    else if (target === "logs") loadLogs();
    else if (target === "settings") loadSettings();
  });
});

// Mobile menu toggle
document.getElementById("mobile-toggle").addEventListener("click", () => {
  document.getElementById("sidebar").classList.toggle("open");
});

// Logout
document.getElementById("btn-logout").addEventListener("click", async () => {
  try {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
  } catch (e) {
    window.location.href = "/login";
  }
});

// 1. DASHBOARD
async function loadDashboard() {
  try {
    const res = await fetch("/api/admin/stats");
    if (res.status === 401) return (window.location.href = "/login");
    const data = await res.json();

    document.getElementById("kpi-total-users").textContent = data.total_users ?? "0";
    document.getElementById("kpi-active-users").textContent = data.active_users ?? "0";
    document.getElementById("kpi-total-nodes").textContent = data.total_nodes ?? "0";
    document.getElementById("kpi-healthy-nodes").textContent = data.healthy_nodes ?? "0";
    document.getElementById("kpi-active-sessions").textContent = data.active_sessions ?? "0";
    document.getElementById("kpi-total-upload").textContent = formatBytes(data.total_upload_bytes);
    document.getElementById("kpi-total-download").textContent = formatBytes(data.total_download_bytes);
    document.getElementById("kpi-ss-users").textContent = data.active_ss_users ?? "0";

    // Sessions table
    const sRes = await fetch("/api/admin/sessions");
    const sessions = await sRes.json();
    const tbody = document.querySelector("#table-dashboard-sessions tbody");
    if (!sessions || sessions.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No active sessions</td></tr>';
    } else {
      tbody.innerHTML = sessions.map(s => `
        <tr>
          <td><span class="badge badge-active">${s.protocol.toUpperCase()}</span></td>
          <td>${s.client_ip}</td>
          <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${s.user_agent || "Unknown"}</td>
          <td>${new Date(s.connected_at).toLocaleTimeString()}</td>
          <td>${new Date(s.last_activity).toLocaleTimeString()}</td>
        </tr>
      `).join("");
    }
  } catch (err) {
    console.error("Dashboard error:", err);
  }
}

// 2. USERS
async function loadUsers() {
  try {
    const res = await fetch("/api/admin/users");
    if (res.status === 401) return (window.location.href = "/login");
    currentUsers = await res.json();
    const tbody = document.querySelector("#table-users tbody");
    if (!currentUsers || currentUsers.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-muted);">No users found. Click "+ Add User" to create one.</td></tr>';
      return;
    }
    tbody.innerHTML = currentUsers.map(u => `
      <tr>
        <td>${u.id}</td>
        <td><strong>${u.username}</strong></td>
        <td>${u.display_name}</td>
        <td><span class="badge ${u.status === 'active' ? 'badge-active' : 'badge-disabled'}">${u.status}</span></td>
        <td style="font-family: monospace; font-size: 0.8rem;">${u.uuid}</td>
        <td>↑ ${formatBytes(u.upload)} / ↓ ${formatBytes(u.download)}</td>
        <td>${u.expires_at || "Never"}</td>
        <td>${u.last_seen_at ? new Date(u.last_seen_at).toLocaleString() : "Never"}</td>
        <td>
          <div style="display: flex; gap: 4px; flex-wrap: wrap;">
            <button class="btn btn-secondary btn-sm" onclick="resetUserUUID(${u.id})">New UUID</button>
            <button class="btn btn-secondary btn-sm" onclick="resetUserToken(${u.id})">New Token</button>
            <button class="btn btn-danger btn-sm" onclick="deleteUser(${u.id})">Del</button>
          </div>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Users error:", err);
  }
}

async function submitAddUser(e) {
  e.preventDefault();
  const u = document.getElementById("new-user-username").value;
  const d = document.getElementById("new-user-display").value;
  const t = parseInt(document.getElementById("new-user-traffic").value) || 0;
  const uuidVal = document.getElementById("new-user-uuid").value.trim() || null;

  try {
    const res = await fetch("/api/admin/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: u, display_name: d, traffic_limit: t, custom_uuid: uuidVal })
    });
    if (res.ok) {
      showToast(`User ${u} created successfully`);
      closeModal("modal-add-user");
      loadUsers();
    } else {
      const err = await res.json();
      showToast(err.detail || "Error creating user", "error");
    }
  } catch (e) {
    showToast("Network error", "error");
  }
}

async function resetUserUUID(id) {
  if (!confirm("Are you sure you want to reset this user's UUID? Connected clients will need to update their configuration.")) return;
  try {
    const res = await fetch(`/api/admin/users/${id}/reset-uuid`, { method: "POST" });
    if (res.ok) {
      showToast("UUID reset successfully");
      loadUsers();
    }
  } catch (e) {
    showToast("Error resetting UUID", "error");
  }
}

async function resetUserToken(id) {
  if (!confirm("Reset subscription token? Existing subscription URLs for this user will stop working.")) return;
  try {
    const res = await fetch(`/api/admin/users/${id}/reset-token`, { method: "POST" });
    if (res.ok) {
      showToast("Subscription token reset successfully");
      loadUsers();
    }
  } catch (e) {
    showToast("Error resetting token", "error");
  }
}

async function deleteUser(id) {
  if (!confirm("Delete this user permanently?")) return;
  try {
    const res = await fetch(`/api/admin/users/${id}`, { method: "DELETE" });
    if (res.ok) {
      showToast("User deleted");
      loadUsers();
    }
  } catch (e) {
    showToast("Error deleting user", "error");
  }
}

// 3. NODES
async function loadNodes() {
  try {
    const res = await fetch("/api/admin/nodes");
    if (res.status === 401) return (window.location.href = "/login");
    const nodes = await res.json();
    const tbody = document.querySelector("#table-nodes tbody");
    if (!nodes || nodes.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-muted);">No nodes configured yet. Click "+ Add Node" to create one.</td></tr>';
      return;
    }
    tbody.innerHTML = nodes.map(n => `
      <tr>
        <td>${n.id}</td>
        <td><strong>${n.name}</strong></td>
        <td><span class="badge badge-active">${n.protocol.toUpperCase()}</span></td>
        <td>${n.address}:${n.port}</td>
        <td>${n.network}</td>
        <td>${n.tls ? "TLS" : "None"}</td>
        <td>${n.region}</td>
        <td><span class="badge ${n.enabled ? 'badge-active' : 'badge-disabled'}">${n.enabled ? 'Enabled' : 'Disabled'}</span></td>
        <td>
          <div style="display: flex; gap: 4px;">
            <button class="btn btn-secondary btn-sm" onclick="testNode(${n.id}, this)">Ping</button>
            <button class="btn btn-danger btn-sm" onclick="deleteNode(${n.id})">Del</button>
          </div>
        </td>
      </tr>
    `).join("");
  } catch (e) {
    console.error("Nodes error:", e);
  }
}

async function submitAddNode(e) {
  e.preventDefault();
  const name = document.getElementById("new-node-name").value;
  const protocol = document.getElementById("new-node-protocol").value;
  const address = document.getElementById("new-node-address").value;
  const port = parseInt(document.getElementById("new-node-port").value);
  const network = document.getElementById("new-node-network").value;
  const tls = document.getElementById("new-node-tls").value === "1";
  const region = document.getElementById("new-node-region").value;

  try {
    const res = await fetch("/api/admin/nodes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, protocol, address, port, network, tls, region })
    });
    if (res.ok) {
      showToast("Node added successfully");
      closeModal("modal-add-node");
      loadNodes();
    }
  } catch (e) {
    showToast("Error adding node", "error");
  }
}

async function testNode(id, btn) {
  btn.textContent = "...";
  try {
    const res = await fetch(`/api/admin/nodes/${id}/test`, { method: "POST" });
    const data = await res.json();
    if (data.status === "online") {
      btn.textContent = `${data.latency_ms} ms`;
      btn.style.color = "var(--primary)";
    } else {
      btn.textContent = "Fail";
      btn.style.color = "var(--danger)";
    }
  } catch (e) {
    btn.textContent = "Err";
  }
}

async function deleteNode(id) {
  if (!confirm("Delete node?")) return;
  try {
    const res = await fetch(`/api/admin/nodes/${id}`, { method: "DELETE" });
    if (res.ok) {
      showToast("Node deleted");
      loadNodes();
    }
  } catch (e) {
    showToast("Error deleting node", "error");
  }
}

// 4. SUBSCRIPTIONS
async function loadSubscriptions() {
  try {
    const res = await fetch("/api/admin/users");
    const users = await res.json();
    const select = document.getElementById("sub-preview-user-select");
    select.innerHTML = users.map(u => `<option value="${u.subscription_token}">${u.username} (${u.display_name})</option>`).join("");
    updateSubPreview();
  } catch (e) {
    console.error("Sub error:", e);
  }
}

function updateSubPreview() {
  const token = document.getElementById("sub-preview-user-select").value;
  if (!token) return;
  const baseUrl = window.location.origin;
  const subUrl = `${baseUrl}/sub/${token}`;
  document.getElementById("sub-url-input").value = subUrl;
  document.getElementById("btn-open-clash").href = `${subUrl}?target=clash`;
  document.getElementById("btn-open-singbox").href = `${subUrl}?target=singbox`;
  document.getElementById("btn-open-base64").href = `${subUrl}?target=base64`;
}

function copySubUrl() {
  const input = document.getElementById("sub-url-input");
  input.select();
  navigator.clipboard.writeText(input.value);
  showToast("Subscription link copied to clipboard!");
}

// 5. SHADOWSOCKS
async function loadShadowSocks() {
  try {
    const res = await fetch("/api/admin/users");
    const users = await res.json();
    const tbody = document.querySelector("#table-ss-creds tbody");
    const rows = [];
    for (const u of users) {
      const ssRes = await fetch(`/api/admin/users/${u.id}/shadowsocks`);
      const ss = await ssRes.json();
      if (ss) {
        rows.push(`
          <tr>
            <td>${u.id}</td>
            <td><strong>${u.username}</strong></td>
            <td>${ss.port}</td>
            <td><span class="badge badge-active">${ss.method}</span></td>
            <td style="font-family: monospace;">••••••••</td>
            <td>${ss.udp ? "Yes" : "No"}</td>
            <td><span class="badge ${ss.enabled ? 'badge-active' : 'badge-disabled'}">${ss.enabled ? 'Active' : 'Disabled'}</span></td>
          </tr>
        `);
      }
    }
    tbody.innerHTML = rows.length > 0 ? rows.join("") : '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No ShadowSocks credentials found</td></tr>';
  } catch (e) {
    console.error("SS error:", e);
  }
}

// 6. PROXYIP
async function loadProxyIPs() {
  try {
    const res = await fetch("/api/admin/proxyips");
    const pips = await res.json();
    const tbody = document.querySelector("#table-proxyips tbody");
    if (!pips || pips.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No ProxyIPs configured</td></tr>';
      return;
    }
    tbody.innerHTML = pips.map(p => `
      <tr>
        <td>${p.id}</td>
        <td>${p.address}</td>
        <td>${p.port}</td>
        <td>${p.region}</td>
        <td>${p.latency_ms > 0 ? p.latency_ms + " ms" : "-"}</td>
        <td><span class="badge ${p.is_active ? 'badge-active' : 'badge-disabled'}">${p.is_active ? 'Active' : 'Inactive'}</span></td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="checkProxyIP(${p.id}, this)">Ping</button>
          <button class="btn btn-danger btn-sm" onclick="deleteProxyIP(${p.id})">Del</button>
        </td>
      </tr>
    `).join("");
  } catch (e) {
    console.error("ProxyIP error:", e);
  }
}

async function submitAddProxyIP(e) {
  e.preventDefault();
  const address = document.getElementById("new-pip-address").value;
  const port = parseInt(document.getElementById("new-pip-port").value);
  const region = document.getElementById("new-pip-region").value;
  try {
    const res = await fetch("/api/admin/proxyips", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ address, port, region })
    });
    if (res.ok) {
      showToast("ProxyIP added");
      closeModal("modal-add-proxyip");
      loadProxyIPs();
    }
  } catch (e) {
    showToast("Error adding ProxyIP", "error");
  }
}

async function checkProxyIP(id, btn) {
  btn.textContent = "...";
  try {
    const res = await fetch(`/api/admin/proxyips/${id}/check`, { method: "POST" });
    const data = await res.json();
    btn.textContent = data.latency_ms > 0 ? `${data.latency_ms} ms` : "Fail";
  } catch (e) {
    btn.textContent = "Err";
  }
}

async function deleteProxyIP(id) {
  try {
    await fetch(`/api/admin/proxyips/${id}`, { method: "DELETE" });
    showToast("ProxyIP removed");
    loadProxyIPs();
  } catch (e) {
    showToast("Error deleting ProxyIP", "error");
  }
}

// 7. DNS
async function loadDNS() {
  try {
    const res = await fetch("/api/admin/dns");
    const list = await res.json();
    const tbody = document.querySelector("#table-dns tbody");
    tbody.innerHTML = list.map(d => `
      <tr>
        <td>${d.id}</td>
        <td><strong>${d.name}</strong></td>
        <td>${d.server_url}</td>
        <td>${d.protocol.toUpperCase()}</td>
        <td>${d.is_default ? 'Yes' : 'No'}</td>
      </tr>
    `).join("");
  } catch (e) {
    console.error("DNS error:", e);
  }
}

async function submitAddDNS(e) {
  e.preventDefault();
  const name = document.getElementById("new-dns-name").value;
  const server_url = document.getElementById("new-dns-url").value;
  const protocol = document.getElementById("new-dns-protocol").value;
  try {
    await fetch("/api/admin/dns", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, server_url, protocol })
    });
    showToast("DNS profile added");
    closeModal("modal-add-dns");
    loadDNS();
  } catch (e) {
    showToast("Error adding DNS", "error");
  }
}

// 8. ROUTING
async function loadRouting() {
  try {
    const res = await fetch("/api/admin/routing");
    const rules = await res.json();
    const tbody = document.querySelector("#table-routing tbody");
    tbody.innerHTML = rules.map(r => `
      <tr>
        <td>${r.id}</td>
        <td><strong>${r.name}</strong></td>
        <td>${r.domain_pattern || "-"}</td>
        <td>${r.ip_cidr || "-"}</td>
        <td>${r.port || "Any"}</td>
        <td><span class="badge badge-active">${r.outbound.toUpperCase()}</span></td>
        <td><button class="btn btn-danger btn-sm" onclick="deleteRouting(${r.id})">Del</button></td>
      </tr>
    `).join("");
  } catch (e) {
    console.error("Routing error:", e);
  }
}

async function submitAddRouting(e) {
  e.preventDefault();
  const name = document.getElementById("new-route-name").value;
  const domain_pattern = document.getElementById("new-route-domain").value.trim() || null;
  const ip_cidr = document.getElementById("new-route-cidr").value.trim() || null;
  const outbound = document.getElementById("new-route-outbound").value;
  try {
    await fetch("/api/admin/routing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, domain_pattern, ip_cidr, outbound })
    });
    showToast("Routing rule added");
    closeModal("modal-add-routing");
    loadRouting();
  } catch (e) {
    showToast("Error adding routing rule", "error");
  }
}

async function deleteRouting(id) {
  try {
    await fetch(`/api/admin/routing/${id}`, { method: "DELETE" });
    showToast("Rule deleted");
    loadRouting();
  } catch (e) {
    showToast("Error deleting rule", "error");
  }
}

// 9. TRAFFIC
async function loadTraffic() {
  try {
    const res = await fetch("/api/admin/stats");
    const data = await res.json();
    document.getElementById("traffic-page-upload").textContent = formatBytes(data.total_upload_bytes);
    document.getElementById("traffic-page-download").textContent = formatBytes(data.total_download_bytes);
  } catch (e) {
    console.error("Traffic error:", e);
  }
}

// 10. LOGS
async function loadLogs() {
  try {
    const res = await fetch("/api/admin/logs");
    const logs = await res.json();
    const tbody = document.querySelector("#table-logs tbody");
    tbody.innerHTML = logs.map(l => `
      <tr>
        <td>${new Date(l.timestamp).toLocaleString()}</td>
        <td><span class="badge badge-active">${l.event}</span></td>
        <td>${l.ip || "-"}</td>
        <td>${l.details || "-"}</td>
      </tr>
    `).join("");
  } catch (e) {
    console.error("Logs error:", e);
  }
}

// 11. SETTINGS
async function loadSettings() {
  try {
    const res = await fetch("/api/admin/settings");
    const settings = await res.json();
    if (settings.public_base_url) document.getElementById("setting-public_base_url").value = settings.public_base_url;
    if (settings.default_domain) document.getElementById("setting-default_domain").value = settings.default_domain;
    if (settings.outbound_mode) document.getElementById("setting-outbound_mode").value = settings.outbound_mode;
    if (settings.outbound_proxy) document.getElementById("setting-outbound_proxy").value = settings.outbound_proxy;
    if (settings.ech_domain) document.getElementById("setting-ech_domain").value = settings.ech_domain;
    if (settings.alpn_list) document.getElementById("setting-alpn_list").value = settings.alpn_list;
  } catch (e) {
    console.error("Settings load error:", e);
  }
}

async function saveSettings(e) {
  e.preventDefault();
  const payload = {
    public_base_url: document.getElementById("setting-public_base_url").value,
    default_domain: document.getElementById("setting-default_domain").value,
    outbound_mode: document.getElementById("setting-outbound_mode").value,
    outbound_proxy: document.getElementById("setting-outbound_proxy").value,
    ech_domain: document.getElementById("setting-ech_domain").value,
    alpn_list: document.getElementById("setting-alpn_list").value,
  };
  try {
    const res = await fetch("/api/admin/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      showToast("System settings updated successfully");
    }
  } catch (e) {
    showToast("Error saving settings", "error");
  }
}

// Initial load
loadDashboard();
