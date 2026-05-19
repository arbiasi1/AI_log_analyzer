import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  Bell,
  BrainCircuit,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  Clock3,
  Cpu,
  Database,
  Download,
  FileText,
  Gauge,
  GitBranch,
  History,
  Layers3,
  LogIn,
  LogOut,
  Loader2,
  Network,
  Play,
  SearchCheck,
  Server,
  Settings,
  ShieldAlert,
  Terminal,
  UploadCloud,
  X,
} from "lucide-react";

import {
  analyzeLogs,
  clearToken,
  fetchAuditEvents,
  fetchCurrentUser,
  fetchHistory,
  fetchOperationalOverview,
  fetchPlatformOverview,
  fetchSampleLogs,
  getStoredToken,
  loginUser,
  logoutUser,
  resolveIncident,
  storeToken,
} from "./api";
import "./styles.css";

const navItems = [
  { id: "command", label: "Command Center", icon: Gauge },
  { id: "services", label: "Services", icon: Server },
  { id: "incidents", label: "Incidents", icon: ShieldAlert },
  { id: "analyzer", label: "Log Analyzer", icon: Terminal },
  { id: "ai", label: "AI Intelligence", icon: BrainCircuit },
  { id: "alerts", label: "Alerts", icon: Bell },
  { id: "history", label: "History", icon: History },
  { id: "settings", label: "Settings", icon: Settings },
];

function App() {
  const [user, setUser] = useState(null);
  const [authReady, setAuthReady] = useState(false);
  const [logs, setLogs] = useState("");
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [overview, setOverview] = useState(null);
  const [platform, setPlatform] = useState(null);
  const [auditEvents, setAuditEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [activeView, setActiveView] = useState("command");

  useEffect(() => {
    bootstrapAuth();
  }, []);

  useEffect(() => {
    if (user) refreshWorkspace();
  }, [user]);

  const stats = useMemo(() => {
    const findings = result?.result?.errors_found || [];
    const services = result?.result?.impacted_services || [];
    return {
      total: findings.length,
      repeated: findings.filter((item) => item.frequency > 1).length,
      high: findings.filter((item) => item.severity === "high").length,
      services: services.length,
    };
  }, [result]);

  async function bootstrapAuth() {
    const token = getStoredToken();
    if (!token) {
      setAuthReady(true);
      return;
    }
    try {
      setUser(await fetchCurrentUser());
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setAuthReady(true);
    }
  }

  async function refreshWorkspace() {
    const [nextHistory, nextOverview, nextPlatform, nextAudit] = await Promise.all([
      fetchHistory().catch(() => []),
      fetchOperationalOverview().catch(() => null),
      fetchPlatformOverview().catch(() => null),
      fetchAuditEvents().catch(() => []),
    ]);
    setHistory(nextHistory);
    setOverview(nextOverview);
    setPlatform(nextPlatform);
    setAuditEvents(nextAudit);
  }

  async function handleLogin(credentials) {
    setError("");
    setLoading(true);
    try {
      const session = await loginUser(credentials);
      storeToken(session.access_token);
      setUser(session.user);
      setActiveView("command");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    await logoutUser().catch(() => null);
    clearToken();
    setUser(null);
    setResult(null);
    setHistory([]);
    setOverview(null);
    setPlatform(null);
    setAuditEvents([]);
    setLogs("");
    setFile(null);
  }

  async function handleAnalyze() {
    setError("");
    if (!logs.trim() && !file) {
      setError("Paste logs or upload a .log/.txt file before analyzing.");
      return;
    }
    setLoading(true);
    try {
      const analysis = await analyzeLogs({ text: logs, file });
      setResult(analysis);
      setActiveView("incidents");
      await refreshWorkspace();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadSample() {
    setError("");
    const sample = await fetchSampleLogs();
    setLogs(sample.logs);
    setFile(null);
  }

  async function handleResolveIncident(id) {
    await resolveIncident(id);
    await refreshWorkspace();
  }

  function exportReport() {
    window.print();
  }

  if (!authReady) return <LoadingShell />;
  if (!user) return <LoginScreen error={error} loading={loading} onLogin={handleLogin} />;

  return (
    <div className="ops-layout">
      <aside className="sidebar">
        <div className="brand-block">
          <span className="brand-mark">AI</span>
          <div>
            <strong>OpsCore</strong>
            <small>AIOps Platform</small>
          </div>
        </div>
        <nav>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={activeView === item.id ? "active" : ""}
                key={item.id}
                onClick={() => setActiveView(item.id)}
              >
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <div>
            <strong>{user.name}</strong>
            <small>{user.team}</small>
          </div>
          <button className="icon-button dark" onClick={handleLogout} title="Logout">
            <LogOut size={17} />
          </button>
        </div>
      </aside>

      <main className="workspace">
        <Topbar user={user} platform={platform} />
        {activeView === "command" && (
          <CommandCenter
            overview={overview}
            platform={platform}
            onAnalyze={() => setActiveView("analyzer")}
            onOpenIncidents={() => setActiveView("incidents")}
          />
        )}
        {activeView === "services" && <ServicesView services={platform?.services || []} />}
        {activeView === "incidents" && (
          <IncidentsView
            incidents={platform?.incidents || []}
            result={result}
            stats={stats}
            onExport={exportReport}
            onResolve={handleResolveIncident}
          />
        )}
        {activeView === "analyzer" && (
          <AnalyzerView
            dragging={dragging}
            error={error}
            file={file}
            loading={loading}
            logs={logs}
            result={result}
            stats={stats}
            onAnalyze={handleAnalyze}
            onClear={() => {
              setLogs("");
              setFile(null);
              setError("");
            }}
            onDragChange={setDragging}
            onFile={(nextFile) => {
              if (!nextFile) return;
              setFile(nextFile);
              setError("");
            }}
            onLoadSample={loadSample}
            onLogs={setLogs}
            onExport={exportReport}
          />
        )}
        {activeView === "ai" && <AiView record={result} platform={platform} onJump={() => setActiveView("analyzer")} />}
        {activeView === "alerts" && <AlertsView rules={platform?.alert_rules || []} deployments={platform?.deployments || []} />}
        {activeView === "history" && <HistoryView history={history} onSelect={(record) => setResult(record)} />}
        {activeView === "settings" && <SettingsView user={user} auditEvents={auditEvents} result={result} />}
      </main>
    </div>
  );
}

function LoadingShell() {
  return (
    <main className="auth-shell">
      <div className="empty-state compact">
        <Loader2 className="spin" size={38} />
        <h2>Preparing secure workspace</h2>
      </div>
    </main>
  );
}

function LoginScreen({ error, loading, onLogin }) {
  const [email, setEmail] = useState("admin@devops.local");
  const [password, setPassword] = useState("admin123");

  function submit(event) {
    event.preventDefault();
    onLogin({ email, password });
  }

  return (
    <main className="auth-shell">
      <section className="login-panel">
        <div>
          <p className="eyebrow">Secure AIOps workspace</p>
          <h1>OpsCore Incident Platform</h1>
          <p>Manage services, incidents, alerts, log intelligence, and AI-assisted remediation from one operational console.</p>
        </div>
        <form onSubmit={submit}>
          <label>
            Email
            <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" />
          </label>
          <label>
            Password
            <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" />
          </label>
          {error && (
            <div className="error-banner">
              <AlertTriangle size={18} />
              {error}
            </div>
          )}
          <button className="primary" disabled={loading}>
            {loading ? <Loader2 className="spin" size={18} /> : <LogIn size={18} />}
            Sign in
          </button>
        </form>
      </section>
    </main>
  );
}

function Topbar({ user, platform }) {
  const activeIncidents = (platform?.incidents || []).filter((item) => item.status !== "resolved").length;
  return (
    <header className="workspace-topbar">
      <div>
        <p className="eyebrow">Production operations</p>
        <h1>Command workspace</h1>
      </div>
      <div className="topbar-cluster">
        <span className="status-pill">
          <Activity size={16} />
          {activeIncidents} active incidents
        </span>
        <span className="status-pill">
          <Cpu size={16} />
          Hybrid AI
        </span>
        <span className="identity-chip">{user.role}</span>
      </div>
    </header>
  );
}

function CommandCenter({ overview, platform, onAnalyze, onOpenIncidents }) {
  const incidents = platform?.incidents || [];
  const active = incidents.filter((item) => item.status !== "resolved");
  const services = platform?.services || [];
  const brief = platform?.copilot_brief;
  return (
    <div className="view-stack">
      <section className="kpi-grid">
        <Kpi icon={Network} label="Services" value={services.length} tone="neutral" />
        <Kpi icon={ShieldAlert} label="Active incidents" value={active.length} tone={active.length ? "danger" : "good"} />
        <Kpi icon={AlertTriangle} label="Critical analyses" value={overview?.critical ?? 0} tone="warning" />
        <Kpi icon={BrainCircuit} label="Avg risk" value={overview?.average_incident_score ?? 0} tone="neutral" />
      </section>

      <section className="command-grid">
        <article className="panel large">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Service health</p>
              <h2>Production map</h2>
            </div>
            <button className="secondary" onClick={onAnalyze}>
              <Terminal size={18} />
              Analyze logs
            </button>
          </div>
          <div className="service-table">
            {services.map((service) => (
              <ServiceRow service={service} key={service.id} />
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">AI copilot</p>
              <h2>{brief?.title || "Command brief"}</h2>
            </div>
          </div>
          <p className="muted-copy">{brief?.summary}</p>
          <List items={brief?.priorities || []} />
          <button className="primary full" onClick={onOpenIncidents}>
            <ShieldAlert size={18} />
            Open incidents
          </button>
        </article>
      </section>
    </div>
  );
}

function ServicesView({ services }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Service catalog</p>
          <h2>Ownership, dependencies, and live risk</h2>
        </div>
      </div>
      <div className="service-cards">
        {services.map((service) => (
          <article className="service-card" key={service.id}>
            <div className="service-card-top">
              <StatusDot status={service.status} />
              <strong>{service.name}</strong>
              <span>{service.risk_score}/100</span>
            </div>
            <p>{service.last_signal}</p>
            <small>Owner: {service.owner}</small>
            <small>Dependencies: {service.dependencies.length ? service.dependencies.join(", ") : "none"}</small>
            <ProgressBar value={service.risk_score} />
          </article>
        ))}
      </div>
    </section>
  );
}

function IncidentsView({ incidents, result, stats, onExport, onResolve }) {
  return (
    <div className="view-stack">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Incident management</p>
            <h2>Active incident queue</h2>
          </div>
        </div>
        {incidents.length ? (
          <div className="incident-list">
            {incidents.map((incident) => (
              <article className="incident-row" key={incident.id}>
                <div>
                  <span className={`severity ${incident.severity}`}>{incident.severity}</span>
                  <h3>{incident.title}</h3>
                  <p>{incident.summary}</p>
                </div>
                <div className="incident-meta">
                  <span>{incident.service}</span>
                  <span>{incident.status}</span>
                  <strong>{incident.risk_score}/100</strong>
                </div>
                {incident.status !== "resolved" && (
                  <button className="secondary" onClick={() => onResolve(incident.id)}>
                    <CheckCircle2 size={18} />
                    Resolve
                  </button>
                )}
              </article>
            ))}
          </div>
        ) : (
          <NoResultView icon={ShieldAlert} title="No incidents created yet" />
        )}
      </section>
      {result && <Results record={result} stats={stats} onExport={onExport} />}
    </div>
  );
}

function AnalyzerView(props) {
  return (
    <div className="analysis-grid">
      <LogIntake {...props} />
      {props.result ? <Results record={props.result} stats={props.stats} onExport={props.onExport} /> : <EmptyState />}
    </div>
  );
}

function LogIntake({
  dragging,
  error,
  file,
  loading,
  logs,
  onAnalyze,
  onClear,
  onDragChange,
  onFile,
  onLoadSample,
  onLogs,
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Log intake</p>
          <h2>Analyze operational evidence</h2>
        </div>
        {(logs || file) && (
          <button className="icon-button" onClick={onClear} title="Clear input">
            <X size={18} />
          </button>
        )}
      </div>
      <label
        className={`drop-zone ${dragging ? "dragging" : ""}`}
        onDragEnter={(event) => {
          event.preventDefault();
          onDragChange(true);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={() => onDragChange(false)}
        onDrop={(event) => {
          event.preventDefault();
          onDragChange(false);
          onFile(event.dataTransfer.files?.[0]);
        }}
      >
        <UploadCloud size={30} />
        <span>{file ? file.name : "Drop .log or .txt evidence"}</span>
        <small>{file ? `${Math.ceil(file.size / 1024)} KB selected` : "Kubernetes, Docker, CI, gateway, database, and app logs"}</small>
        <input type="file" accept=".log,.txt,text/plain" onChange={(event) => onFile(event.target.files?.[0])} />
      </label>
      <textarea
        value={logs}
        onChange={(event) => onLogs(event.target.value)}
        placeholder="[ERROR] Database connection failed at 03:45&#10;[CRITICAL] API gateway returned 504 for checkout-service&#10;[WARN] Queue worker lag above threshold"
      />
      {error && (
        <div className="error-banner">
          <AlertTriangle size={18} />
          {error}
        </div>
      )}
      <div className="action-row">
        <button className="secondary" onClick={onLoadSample}>
          <FileText size={18} />
          Load sample
        </button>
        <button className="primary" onClick={onAnalyze} disabled={loading}>
          {loading ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
          Analyze and triage
        </button>
      </div>
    </section>
  );
}

function Results({ record, stats, onExport }) {
  const { result } = record;
  return (
    <section className="panel result-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Analysis result</p>
          <h2>{record.source}</h2>
        </div>
        <div className="result-actions">
          <span className={`ai-badge ${result.ai_engine === "openai" ? "live" : ""}`}>
            <BrainCircuit size={16} />
            {result.ai_engine === "openai" ? result.ai_model : "local-ml"}
          </span>
          <button className="secondary" onClick={onExport}>
            <Download size={18} />
            Export
          </button>
        </div>
      </div>
      <div className={`health-banner ${result.overall_health}`}>
        <AlertTriangle size={24} />
        <div>
          <span>Overall health</span>
          <strong>{result.overall_health}</strong>
        </div>
        <RiskDial value={result.incident_score} />
      </div>
      <div className="metric-row">
        <Metric label="Patterns" value={stats.total} />
        <Metric label="Repeated" value={stats.repeated} />
        <Metric label="High severity" value={stats.high} />
        <Metric label="Services" value={stats.services} />
      </div>
      <article className="summary-block">
        <h3>Executive summary</h3>
        <p>{result.summary}</p>
        <small className="provider-note">{result.ai_provider_status}</small>
      </article>
      <FindingsTable findings={result.errors_found} />
    </section>
  );
}

function AiView({ record, platform, onJump }) {
  if (!record) return <NoResultView icon={BrainCircuit} onJump={onJump} title="No AI report selected" />;
  const result = record.result;
  return (
    <div className="view-stack">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">AI intelligence</p>
            <h2>Reasoning, anomaly signals, and runbook</h2>
          </div>
          <span className={`ai-badge ${result.ai_engine === "openai" ? "live" : ""}`}>
            <BrainCircuit size={16} />
            {result.ai_provider_status}
          </span>
        </div>
        <div className="ai-grid">
          {result.ml_signals.map((signal) => (
            <article className="signal-card" key={signal.name}>
              <div className="signal-top">
                <BrainCircuit size={22} />
                <span>{signal.trend}</span>
              </div>
              <h3>{signal.name}</h3>
              <ProgressBar value={signal.score} />
              <strong>{signal.score}/100</strong>
              <p>{signal.explanation}</p>
              <small>{Math.round(signal.confidence * 100)}% confidence</small>
            </article>
          ))}
        </div>
      </section>
      <section className="split-grid">
        <article className="panel">
          <h2>Runbook</h2>
          <div className="runbook">
            {result.runbook.map((step) => (
              <div className="runbook-step" key={step.title}>
                <ClipboardCheck size={20} />
                <div>
                  <strong>{step.title}</strong>
                  {step.command && (
                    <code>
                      <Terminal size={14} />
                      {step.command}
                    </code>
                  )}
                  <p>{step.rationale}</p>
                </div>
              </div>
            ))}
          </div>
        </article>
        <article className="panel">
          <h2>Fleet learning</h2>
          <List
            items={(platform?.services || []).slice(0, 4).map((item) => `${item.name}: ${item.risk_score}/100 risk`)}
          />
        </article>
      </section>
    </div>
  );
}

function AlertsView({ rules, deployments }) {
  return (
    <div className="split-grid">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Alert engine</p>
            <h2>Rules and thresholds</h2>
          </div>
        </div>
        <div className="rule-list">
          {rules.map((rule) => (
            <article className="rule-card" key={rule.id}>
              <Bell size={19} />
              <div>
                <strong>{rule.name}</strong>
                <p>{rule.condition}</p>
                <small>{rule.service} · threshold {rule.threshold} · cooldown {rule.cooldown_minutes}m</small>
              </div>
              <span>{rule.status}</span>
            </article>
          ))}
        </div>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Deploy correlation</p>
            <h2>Recent releases</h2>
          </div>
        </div>
        <div className="rule-list">
          {deployments.map((deploy) => (
            <article className="rule-card" key={deploy.id}>
              <GitBranch size={19} />
              <div>
                <strong>{deploy.version}</strong>
                <p>{deploy.risk_note}</p>
                <small>{deploy.service} · {deploy.actor}</small>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function HistoryView({ history, onSelect }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Evidence history</p>
          <h2>Saved analyses</h2>
        </div>
      </div>
      {history.length ? (
        <div className="history-list">
          {history.map((record) => (
            <button className="history-item" key={record.id} onClick={() => onSelect(record)}>
              <div>
                <strong>{record.source}</strong>
                <p>{record.raw_log_preview}</p>
              </div>
              <span className={`mini-health ${record.result.overall_health}`}>{record.result.overall_health}</span>
              <span className="risk-chip">{record.result.incident_score}/100</span>
              <ChevronRight size={18} />
            </button>
          ))}
        </div>
      ) : (
        <NoResultView icon={History} title="No analyses yet" />
      )}
    </section>
  );
}

function SettingsView({ user, auditEvents, result }) {
  return (
    <div className="split-grid">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Workspace settings</p>
            <h2>Identity and AI mode</h2>
          </div>
        </div>
        <div className="settings-list">
          <Metric label="User" value={user.name} />
          <Metric label="Role" value={user.role} />
          <Metric label="Team" value={user.team} />
          <Metric label="AI engine" value={result?.result?.ai_engine || "local-ml"} />
        </div>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Audit trail</p>
            <h2>Recent activity</h2>
          </div>
        </div>
        <div className="audit-list">
          {auditEvents.map((event) => (
            <article className="audit-item" key={`${event.created_at}-${event.action}-${event.detail}`}>
              <Clock3 size={18} />
              <div>
                <strong>{event.action}</strong>
                <p>{event.detail}</p>
              </div>
              <small>{new Date(event.created_at).toLocaleString()}</small>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="empty-state">
      <SearchCheck size={44} />
      <h2>No analysis selected</h2>
      <p>Run an evidence analysis to generate incident intelligence, service impact, SLO risk, and runbook steps.</p>
    </div>
  );
}

function FindingsTable({ findings }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Severity</th>
            <th>Error pattern</th>
            <th>Frequency</th>
            <th>Suggested fix</th>
          </tr>
        </thead>
        <tbody>
          {findings.length ? (
            findings.map((item) => (
              <tr key={`${item.error}-${item.frequency}`}>
                <td><span className={`severity ${item.severity}`}>{item.severity}</span></td>
                <td><strong>{item.error}</strong><small>{item.possible_cause}</small></td>
                <td>{item.frequency}x</td>
                <td>{item.suggested_fix}</td>
              </tr>
            ))
          ) : (
            <tr><td colSpan="4" className="quiet-cell">No notable error patterns found.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function ServiceRow({ service }) {
  return (
    <div className="service-row">
      <StatusDot status={service.status} />
      <div>
        <strong>{service.name}</strong>
        <small>{service.owner}</small>
      </div>
      <ProgressBar value={service.risk_score} />
      <span>{service.risk_score}/100</span>
    </div>
  );
}

function Kpi({ icon: Icon, label, value, tone }) {
  return (
    <article className={`kpi-card ${tone}`}>
      <Icon size={22} />
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </article>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function RiskDial({ value }) {
  return (
    <div className="risk-dial">
      <span>{value}</span>
      <small>risk</small>
    </div>
  );
}

function StatusDot({ status }) {
  return <span className={`status-dot ${status}`} />;
}

function ProgressBar({ value }) {
  return (
    <div className="progress-track">
      <span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}

function List({ items, empty = "Nothing to show yet." }) {
  if (!items?.length) return <p className="muted-copy">{empty}</p>;
  return (
    <ul className="clean-list">
      {items.map((item) => <li key={item}>{item}</li>)}
    </ul>
  );
}

function NoResultView({ icon: Icon, title, onJump }) {
  return (
    <div className="empty-state compact">
      <Icon size={38} />
      <h2>{title}</h2>
      <p>Use the analyzer or select a saved record to populate this workspace.</p>
      {onJump && (
        <button className="primary" onClick={onJump}>
          <Terminal size={18} />
          Open analyzer
        </button>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App />);
