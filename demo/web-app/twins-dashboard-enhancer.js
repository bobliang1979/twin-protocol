/**
 * twins-dashboard-enhancer.js — 仪表盘增强模块
 * 
 * 注入方式: 在浏览器控制台粘贴执行，或加到 index.html 的 <script> 中
 * 
 * 新增功能:
 * 1. Raw JSON 面板 — 点击消息展开完整的 JSON 格式化视图
 * 2. 工具请求↔响应配对 — 相同 request_id 的 tool_request / tool_result 自动连线
 * 3. Agent 活跃心跳指示器 — 实时显示两端状态
 * 4. 消息统计仪表盘 — 按类型和来源统计
 * 5. 自动滚动开关
 */

(function enhanceDashboard() {

  // ── 1. Inject CSS ──────────────────────────────────
  const style = document.createElement("style");
  style.textContent = `
    .tw-enhance-bar {
      display: flex; gap: 12px; align-items: center;
      padding: 6px 24px; background: #0d1117;
      border-bottom: 1px solid #30363d; font-size: 12px;
    }
    .tw-enhance-bar .stat {
      display: flex; align-items: center; gap: 4px;
    }
    .tw-enhance-bar .stat .num { color: #58a6ff; font-weight: 600; }
    .tw-enhance-bar .stat .num.green { color: #3fb950; }
    .tw-enhance-bar .stat .num.purple { color: #a371f7; }
    .tw-enhance-bar .stat .num.orange { color: #d29922; }

    .tw-paired {
      border-left: 3px solid #1f6feb !important;
      background: #0d1a2b !important;
    }
    .tw-paired .pair-badge {
      display: inline-block; font-size: 10px;
      background: #1f6feb33; color: #58a6ff;
      padding: 0 6px; border-radius: 4px; margin-left: 4px;
    }

    .tw-json-panel {
      display: none; position: fixed; top: 50%; left: 50%;
      transform: translate(-50%, -50%); width: 80%; max-width: 700px;
      max-height: 70vh; background: #161b22; border: 1px solid #30363d;
      border-radius: 12px; z-index: 1000; overflow: hidden;
      box-shadow: 0 16px 48px rgba(0,0,0,0.6);
    }
    .tw-json-panel.show { display: block; }
    .tw-json-panel .header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 12px 16px; border-bottom: 1px solid #30363d;
      background: #1c2333;
    }
    .tw-json-panel .header h3 { font-size: 14px; font-weight: 600; margin: 0; }
    .tw-json-panel .header .close {
      cursor: pointer; background: none; border: none;
      color: #8b949e; font-size: 18px;
    }
    .tw-json-panel .header .close:hover { color: #f85149; }
    .tw-json-panel pre {
      padding: 16px; margin: 0; overflow: auto;
      font-size: 12px; line-height: 1.6; max-height: calc(70vh - 48px);
      background: #0d1117; color: #e6edf3;
    }

    .tw-overlay {
      display: none; position: fixed; top: 0; left: 0;
      width: 100%; height: 100%; background: rgba(0,0,0,0.5);
      z-index: 999;
    }
    .tw-overlay.show { display: block; }

    .entry.clickable { cursor: pointer; }
    .entry.clickable:hover { border-color: #58a6ff; }

    .tw-heartbeat {
      display: inline-flex; align-items: center; gap: 4px;
      margin-left: 12px; font-size: 11px;
    }
    .tw-heartbeat .dot {
      width: 6px; height: 6px; border-radius: 50%;
      animation: tw-pulse 2s ease-in-out infinite;
    }
    .tw-heartbeat .dot.alive { background: #3fb950; }
    .tw-heartbeat .dot.dead { background: #f85149; animation: none; }
    @keyframes tw-pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }

    .tw-connection-status {
      margin-left: auto; font-size: 11px; display: flex; align-items: center; gap: 6px;
    }
    .tw-connection-status .dot { width: 8px; height: 8px; border-radius: 50%; }
    .tw-connection-status .dot.connected { background: #3fb950; }
    .tw-connection-status .dot.disconnected { background: #f85149; }
  `;
  document.head.appendChild(style);

  // ── 2. Enhancement Bar ─────────────────────────────
  const statusBar = document.querySelector(".status-bar");
  if (statusBar) {
    const bar = document.createElement("div");
    bar.className = "tw-enhance-bar";
    bar.id = "tw-enhance-bar";
    bar.innerHTML = `
      <span class="stat">📨 总消息: <span class="num" id="tw-total-msgs">0</span></span>
      <span class="stat">🔧 工具请求: <span class="num orange" id="tw-tool-reqs">0</span></span>
      <span class="stat">✅ 工具结果: <span class="num green" id="tw-tool-results">0</span></span>
      <span class="stat">💬 文本消息: <span class="num purple" id="tw-text-msgs">0</span></span>
      <span class="tw-heartbeat"><span class="dot alive" id="tw-hb-hermes"></span> Hermes</span>
      <span class="tw-heartbeat"><span class="dot alive" id="tw-hb-codex"></span> Codex++</span>
      <label style="margin-left:12px;font-size:11px;cursor:pointer">
        <input type="checkbox" id="tw-scroll-toggle" checked> 自动滚动
      </label>
      <span class="tw-connection-status">
        <span class="dot connected" id="tw-conn-dot"></span>
        <span id="tw-conn-text">已连接</span>
      </span>
    `;
    statusBar.parentNode.insertBefore(bar, statusBar.nextSibling);
  }

  // ── 3. JSON Panel ──────────────────────────────────
  const overlay = document.createElement("div");
  overlay.className = "tw-overlay";
  overlay.id = "tw-overlay";
  document.body.appendChild(overlay);

  const jsonPanel = document.createElement("div");
  jsonPanel.className = "tw-json-panel";
  jsonPanel.id = "tw-json-panel";
  jsonPanel.innerHTML = `
    <div class="header">
      <h3>📄 Raw JSON</h3>
      <button class="close" id="tw-json-close">&times;</button>
    </div>
    <pre id="tw-json-content">点击消息查看完整 JSON</pre>
  `;
  document.body.appendChild(jsonPanel);

  document.getElementById("tw-json-close").onclick = closeJSON;
  document.getElementById("tw-overlay").onclick = closeJSON;
  function closeJSON() {
    document.getElementById("tw-json-panel").classList.remove("show");
    document.getElementById("tw-overlay").classList.remove("show");
  }

  // ── 4. Data Tracking ───────────────────────────────
  const state = { hermesMsgs: [], codexMsgs: [], pairs: {} };
  let lastCount = 0;

  async function refreshStats() {
    try {
      const res = await fetch("/api/outbox");
      const text = await res.text();
      const lines = text.trim().split("\n").filter(Boolean);
      const msgs = lines.map(l => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);

      if (msgs.length === lastCount) return;
      lastCount = msgs.length;

      // Count
      const counts = { total: msgs.length, tool_req: 0, tool_res: 0, text: 0 };
      msgs.forEach(m => {
        if (m.type === "tool_request") counts.tool_req++;
        else if (m.type === "tool_result") counts.tool_res++;
        else counts.text++;
      });

      document.getElementById("tw-total-msgs").textContent = counts.total;
      document.getElementById("tw-tool-reqs").textContent = counts.tool_req;
      document.getElementById("tw-tool-results").textContent = counts.tool_res;
      document.getElementById("tw-text-msgs").textContent = counts.text;

      // Pair detection
      msgs.forEach(m => {
        if (m.type === "tool_request" && m.request_id) {
          state.pairs[m.request_id] = { req: m, res: null };
        }
        if (m.type === "tool_result" && m.request_id && state.pairs[m.request_id]) {
          state.pairs[m.request_id].res = m;
        }
      });

      // Mark paired entries in DOM
      Object.values(state.pairs).forEach(p => {
        if (!p.res) return;
        // Find DOM elements that match this pair and add class
        document.querySelectorAll(".entry").forEach(el => {
          const text = el.textContent || "";
          if (text.includes(p.req.request_id?.slice(0,8))) {
            el.classList.add("tw-paired");
            // Add pair badge
            const meta = el.querySelector(".meta");
            if (meta && !meta.querySelector(".pair-badge")) {
              const badge = document.createElement("span");
              badge.className = "pair-badge";
              badge.textContent = `⏱ ${p.req.timestamp?.slice(11,19) || "?"} → ${p.res._ts?.slice(11,19) || "?"}`;
              if (p.res.execution_ms) badge.textContent += ` (${p.res.execution_ms}ms)`;
              meta.appendChild(badge);
            }
          }
        });
      });

      // Make entries clickable for JSON view
      document.querySelectorAll(".entry:not(.clickable)").forEach(el => {
        el.classList.add("clickable");
        el.addEventListener("click", function(e) {
          if (e.target.closest(".meta")) return;
          const text = this.querySelector(".body")?.textContent || "";
          // Find matching message from data
          for (const m of msgs) {
            const jsonStr = JSON.stringify(m, null, 2);
            if (jsonStr.includes(text.slice(0, 30))) {
              document.getElementById("tw-json-content").textContent = jsonStr;
              document.getElementById("tw-json-panel").classList.add("show");
              document.getElementById("tw-overlay").classList.add("show");
              break;
            }
          }
        });
      });

      // Heartbeat detection (alive if message in last 30s)
      const now = Date.now();
      const hermesAlive = msgs.some(m => {
        if (!m.timestamp) return false;
        const ts = new Date(m.timestamp).getTime();
        return m.source === "hermes" && (now - ts) < 30000;
      });
      const codexAlive = msgs.some(m => {
        if (!m.timestamp) return false;
        const ts = new Date(m.timestamp).getTime();
        return m.source === "codex" && (now - ts) < 30000;
      });
      document.getElementById("tw-hb-hermes").className = "dot " + (hermesAlive ? "alive" : "dead");
      document.getElementById("tw-hb-codex").className = "dot " + (codexAlive ? "alive" : "dead");

    } catch (e) {
      document.getElementById("tw-conn-dot").className = "dot disconnected";
      document.getElementById("tw-conn-text").textContent = "断开: " + e.message;
    }
  }

  // ── 5. Auto-scroll Toggle ──────────────────────────
  setTimeout(() => {
    const toggle = document.getElementById("tw-scroll-toggle");
    if (toggle) {
      toggle.addEventListener("change", function() {
        const logs = document.querySelectorAll(".log");
        logs.forEach(log => {
          if (!this.checked) {
            log.style.overflowY = "auto";
          } else {
            log.scrollTop = log.scrollHeight;
          }
        });
      });
    }
  }, 500);

  // ── 6. Start ────────────────────────────────────────
  console.log("⚡ Twins Dashboard Enhancer loaded");
  refreshStats();
  setInterval(refreshStats, 2000);

})();
