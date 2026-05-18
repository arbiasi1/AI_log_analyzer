import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Database,
  Download,
  FileText,
  Flame,
  History,
  Loader2,
  Play,
  ServerCrash,
  UploadCloud,
  X,
} from "lucide-react";

import { analyzeLogs, fetchHistory, fetchSampleLogs } from "./api";
import "./styles.css";

const emptyResult = null;

function App() {
  const [logs, setLogs] = useState("");
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(emptyResult);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [activeView, setActiveView] = useState("analysis");

  useEffect(() => {
    refreshHistory();
  }, []);

  const stats = useMemo(() => {
    const findings = result?.result?.errors_found || [];
    return {
      total: findings.length,
      repeated: findings.filter((item) => item.frequency > 1).length,
      high: findings.filter((item) => item.severity === "high").length,
    };
  }, [result]);

  async function refreshHistory() {
    try {
      setHistory(await fetchHistory());
    } catch {
      setHistory([]);
    }
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
      setActiveView("analysis");
      await refreshHistory();
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

  function acceptFile(nextFile) {
    if (!nextFile) return;
    setFile(nextFile);
    setError("");
  }

  function clearInput() {
    setLogs("");
    setFile(null);
    setError("");
  }

  function exportReport() {
    window.print();
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">DevOps diagnostics</p>
          <h1>AI Log Analyzer</h1>
        </div>
        <div className="status-pill">
          <Database size={16} />
          Mock LLM ready
        </div>
      </header>

      <section className="toolbar" aria-label="Primary views">
        <button className={activeView === "analysis" ? "active" : ""} onClick={() => setActiveView("analysis")}>
          <ServerCrash size={18} />
          Analyze
        </button>
        <button className={activeView === "history" ? "active" : ""} onClick={() => setActiveView("history")}>
          <History size={18} />
          History
        </button>
      </section>

      {activeView === "analysis" ? (
        <div className="dashboard-grid">
          <section className="input-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Log intake</p>
                <h2>Upload or paste logs</h2>
              </div>
              {(logs || file) && (
                <button className="icon-button" onClick={clearInput} title="Clear input" aria-label="Clear input">
                  <X size={18} />
                </button>
              )}
            </div>

            <label
              className={`drop-zone ${dragging ? "dragging" : ""}`}
              onDragEnter={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragOver={(event) => event.preventDefault()}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => {
                event.preventDefault();
                setDragging(false);
                acceptFile(event.dataTransfer.files?.[0]);
              }}
            >
              <UploadCloud size={30} />
              <span>{file ? file.name : "Drop a .log or .txt file here"}</span>
              <small>{file ? `${Math.ceil(file.size / 1024)} KB selected` : "Docker, server, CI, and application logs"}</small>
              <input
                type="file"
                accept=".log,.txt,text/plain"
                onChange={(event) => acceptFile(event.target.files?.[0])}
              />
            </label>

            <textarea
              value={logs}
              onChange={(event) => setLogs(event.target.value)}
              placeholder="[ERROR] Database connection failed at 03:45&#10;[WARN] High memory usage detected&#10;[ERROR] Timeout connecting to auth service&#10;[INFO] Server restarted successfully"
            />

            {error && (
              <div className="error-banner">
                <AlertTriangle size={18} />
                {error}
              </div>
            )}

            <div className="action-row">
              <button className="secondary" onClick={loadSample}>
                <FileText size={18} />
                Load sample
              </button>
              <button className="primary" onClick={handleAnalyze} disabled={loading}>
                {loading ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
                Analyze Logs
              </button>
            </div>
          </section>

          <section className="results-panel">
            {result ? (
              <Results record={result} stats={stats} onExport={exportReport} />
            ) : (
              <EmptyState />
            )}
          </section>
        </div>
      ) : (
        <HistoryView
          history={history}
          onSelect={(record) => {
            setResult(record);
            setActiveView("analysis");
          }}
        />
      )}
    </main>
  );
}

function EmptyState() {
  return (
    <div className="empty-state">
      <Flame size={42} />
      <h2>Production-style diagnostics will appear here</h2>
      <p>Run an analysis to see grouped failures, severity, likely cause, and fix guidance.</p>
    </div>
  );
}

function Results({ record, stats, onExport }) {
  const { result } = record;
  return (
    <div className="result-stack" id="report">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Analysis result</p>
          <h2>{record.source}</h2>
        </div>
        <button className="secondary" onClick={onExport}>
          <Download size={18} />
          Export PDF
        </button>
      </div>

      <div className={`health-banner ${result.overall_health}`}>
        {result.overall_health === "good" ? <CheckCircle2 size={24} /> : <AlertTriangle size={24} />}
        <div>
          <span>Overall health</span>
          <strong>{result.overall_health}</strong>
        </div>
      </div>

      <div className="metric-row">
        <Metric label="Patterns" value={stats.total} />
        <Metric label="Repeated" value={stats.repeated} />
        <Metric label="High severity" value={stats.high} />
      </div>

      <article className="summary-block">
        <h3>Summary</h3>
        <p>{result.summary}</p>
      </article>

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
            {result.errors_found.length ? (
              result.errors_found.map((item) => (
                <tr className={item.frequency > 1 ? "repeated" : ""} key={`${item.error}-${item.frequency}`}>
                  <td>
                    <span className={`severity ${item.severity}`}>{item.severity}</span>
                  </td>
                  <td>
                    <strong>{item.error}</strong>
                    <small>{item.possible_cause}</small>
                  </td>
                  <td>{item.frequency}x</td>
                  <td>{item.suggested_fix}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="4" className="quiet-cell">
                  No notable error patterns found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <article className="root-cause">
        <h3>Root Cause Analysis</h3>
        <p>{result.root_cause_analysis}</p>
      </article>
    </div>
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

function HistoryView({ history, onSelect }) {
  return (
    <section className="history-view">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Saved in memory</p>
          <h2>Previous analyses</h2>
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
              <span className="time">
                <Clock3 size={14} />
                {new Date(record.created_at).toLocaleString()}
              </span>
            </button>
          ))}
        </div>
      ) : (
        <div className="empty-state compact">
          <History size={36} />
          <h2>No analyses yet</h2>
          <p>Run the analyzer once and this page will keep the latest reports for this server process.</p>
        </div>
      )}
    </section>
  );
}

createRoot(document.getElementById("root")).render(<App />);
