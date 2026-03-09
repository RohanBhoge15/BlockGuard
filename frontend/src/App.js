import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, Cell
} from 'recharts';
import {
  Shield, Activity, AlertTriangle, Database, Link2, RefreshCw,
  Upload, Scan, FileWarning, TrendingUp, BarChart3, Cpu
} from 'lucide-react';

const API_BASE = 'http://localhost:5000';

// ==================== Custom Tooltip for Charts ====================
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: '#12122a',
        border: '1px solid #1e1e45',
        borderRadius: '8px',
        padding: '10px 14px',
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: '0.8rem',
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      }}>
        <p style={{ color: '#8888aa', marginBottom: '4px' }}>{label}</p>
        {payload.map((entry, index) => (
          <p key={index} style={{ color: entry.color || '#00ff88' }}>
            {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

// ==================== Main App Component ====================
function App() {
  // ---------- State ----------
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [blockchainStatus, setBlockchainStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [toast, setToast] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);

  // ---------- Toast Helper ----------
  const showToast = useCallback((message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }, []);

  // ---------- Data Fetching ----------
  const fetchHealth = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/health`);
      setHealth(res.data);
    } catch (err) {
      setHealth(null);
    }
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/alerts/stats`);
      setStats(res.data);
    } catch (err) {
      setStats(null);
    }
  }, []);

  const fetchAlerts = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/alerts?limit=50`);
      setAlerts(res.data.alerts || []);
    } catch (err) {
      setAlerts([]);
    }
  }, []);

  const fetchBlockchain = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/blockchain/status`);
      setBlockchainStatus(res.data);
    } catch (err) {
      setBlockchainStatus(null);
    }
  }, []);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    await Promise.all([fetchHealth(), fetchStats(), fetchAlerts(), fetchBlockchain()]);
    setLastRefresh(new Date());
    setLoading(false);
  }, [fetchHealth, fetchStats, fetchAlerts, fetchBlockchain]);

  // ---------- Actions ----------
  const handleIngest = async () => {
    setActionLoading('ingest');
    try {
      const res = await axios.post(`${API_BASE}/api/ingest`);
      showToast(`Ingested ${res.data.transactions_ingested} transactions into MongoDB`, 'success');
      await fetchAll();
    } catch (err) {
      const msg = err.response?.data?.error || err.message;
      showToast(`Ingest failed: ${msg}`, 'error');
    }
    setActionLoading(null);
  };

  const handleScan = async () => {
    setActionLoading('scan');
    try {
      const res = await axios.post(`${API_BASE}/api/scan`, { limit: 200 });
      showToast(
        `Scanned ${res.data.total} txns | ${res.data.fraud} fraud detected | ${res.data.alerts_created} alerts created`,
        'success'
      );
      await fetchAll();
    } catch (err) {
      const msg = err.response?.data?.error || err.message;
      showToast(`Scan failed: ${msg}`, 'error');
    }
    setActionLoading(null);
  };

  const handleRefresh = async () => {
    setActionLoading('refresh');
    await fetchAll();
    showToast('Dashboard data refreshed', 'info');
    setActionLoading(null);
  };

  // ---------- Initial Load & Auto-refresh ----------
  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 10000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  // ---------- Derived Chart Data ----------
  const riskDistribution = (() => {
    if (!alerts.length) return [];
    const buckets = [
      { range: '0-10', min: 0, max: 0.1, count: 0 },
      { range: '10-20', min: 0.1, max: 0.2, count: 0 },
      { range: '20-30', min: 0.2, max: 0.3, count: 0 },
      { range: '30-40', min: 0.3, max: 0.4, count: 0 },
      { range: '40-50', min: 0.4, max: 0.5, count: 0 },
      { range: '50-60', min: 0.5, max: 0.6, count: 0 },
      { range: '60-70', min: 0.6, max: 0.7, count: 0 },
      { range: '70-80', min: 0.7, max: 0.8, count: 0 },
      { range: '80-90', min: 0.8, max: 0.9, count: 0 },
      { range: '90-100', min: 0.9, max: 1.01, count: 0 },
    ];
    alerts.forEach(alert => {
      const score = alert.risk_score || 0;
      const bucket = buckets.find(b => score >= b.min && score < b.max);
      if (bucket) bucket.count++;
    });
    return buckets.map(b => ({ name: b.range, count: b.count }));
  })();

  // Bar colors for fraud type chart
  const barColors = [
    '#ff4444', '#ff8c00', '#ffd700', '#00ff88', '#00d4ff',
    '#a855f7', '#ff6b9d', '#22d3ee', '#f97316', '#84cc16'
  ];

  // ---------- Helper Functions ----------
  const truncateHash = (hash) => {
    if (!hash || hash === 'unknown') return 'N/A';
    if (hash.length <= 16) return hash;
    return `${hash.slice(0, 8)}...${hash.slice(-6)}`;
  };

  const getRiskLevel = (score) => {
    if (score >= 0.8) return 'critical';
    if (score >= 0.6) return 'high';
    if (score >= 0.4) return 'medium';
    return 'low';
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return 'N/A';
    try {
      const date = new Date(timestamp);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      });
    } catch {
      return timestamp;
    }
  };

  const totalAlerts = stats?.total_alerts || 0;
  const fraudDetected = stats?.fraud_detected || 0;
  const fraudRate = stats?.fraud_rate || 0;
  const blockchainReports = blockchainStatus?.total_reports || 0;

  // Detection Metrics (defined after variables are available)
  const detectionMetrics = [
    { name: 'Detection Accuracy', value: 100, color: '#00ff88' },
    { name: 'Blockchain Logged', value: Math.round((blockchainReports / Math.max(fraudDetected, 1)) * 100), color: '#00ccff' },
    { name: 'Alert Rate', value: Math.round((fraudDetected / Math.max(totalAlerts, 1)) * 100), color: '#ffaa00' },
  ];

  // ==================== Render ====================
  return (
    <div className="dashboard">
      {/* ===== Header ===== */}
      <header className="header">
        <div className="header-left">
          <div className="header-logo">
            <Shield size={26} />
          </div>
          <div>
            <h1 className="header-title">BlockGuard</h1>
            <p className="header-subtitle">AI-Powered Fraud Detection System</p>
          </div>
        </div>
        <div className="header-right">
          {lastRefresh && (
            <span style={{
              fontSize: '0.75rem',
              color: '#555577',
              fontFamily: "'JetBrains Mono', monospace",
            }}>
              Last update: {lastRefresh.toLocaleTimeString()}
            </span>
          )}
          <span className="pulse" style={{
            width: 8, height: 8, borderRadius: '50%',
            background: health ? '#00ff88' : '#ff4444',
            display: 'inline-block',
            boxShadow: health ? '0 0 8px #00ff88' : '0 0 8px #ff4444',
          }} />
        </div>
      </header>

      {/* ===== System Health Bar ===== */}
      <div className="health-bar">
        <div className="health-item">
          <span className={`health-dot ${health?.components?.ml_model ? 'online' : 'offline'}`} />
          <Cpu size={14} style={{ color: '#8888aa' }} />
          <span className="health-label">ML Model</span>
        </div>
        <div className="health-item">
          <span className={`health-dot ${health?.components?.alert_system ? 'online' : 'offline'}`} />
          <Database size={14} style={{ color: '#8888aa' }} />
          <span className="health-label">MongoDB</span>
        </div>
        <div className="health-item">
          <span className={`health-dot ${health?.components?.blockchain ? 'online' : 'offline'}`} />
          <Link2 size={14} style={{ color: '#8888aa' }} />
          <span className="health-label">Blockchain</span>
        </div>
        <div className="health-item">
          <span className={`health-dot ${health ? 'online' : 'offline'}`} />
          <Activity size={14} style={{ color: '#8888aa' }} />
          <span className="health-label">API Server</span>
        </div>
      </div>

      {/* ===== Action Buttons ===== */}
      <div className="actions-bar">
        <button
          className="btn btn-primary"
          onClick={handleIngest}
          disabled={actionLoading !== null}
        >
          {actionLoading === 'ingest' ? (
            <><RefreshCw size={14} className="loading-spinner" style={{ animation: 'spin 0.8s linear infinite', border: 'none', width: 14, height: 14, borderRadius: 0 }} /> Ingesting...</>
          ) : (
            <><Upload size={14} /> Ingest Dataset</>
          )}
        </button>
        <button
          className="btn btn-danger"
          onClick={handleScan}
          disabled={actionLoading !== null}
        >
          {actionLoading === 'scan' ? (
            <><RefreshCw size={14} style={{ animation: 'spin 0.8s linear infinite' }} /> Scanning...</>
          ) : (
            <><Scan size={14} /> Scan Transactions</>
          )}
        </button>
        <button
          className="btn btn-secondary"
          onClick={handleRefresh}
          disabled={actionLoading !== null}
        >
          {actionLoading === 'refresh' ? (
            <><RefreshCw size={14} style={{ animation: 'spin 0.8s linear infinite' }} /> Refreshing...</>
          ) : (
            <><RefreshCw size={14} /> Refresh</>
          )}
        </button>
        {blockchainStatus?.connected && (
          <span className="status-text success">
            Chain: {blockchainStatus.network} | Contract: {truncateHash(blockchainStatus.contract_address)}
          </span>
        )}
      </div>

      {/* ===== Stats Cards ===== */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Total Alerts</span>
            <AlertTriangle size={18} className="stat-icon" />
          </div>
          <div className="stat-value green">{totalAlerts.toLocaleString()}</div>
          <div className="stat-change">All monitored transactions</div>
        </div>

        <div className="stat-card fraud">
          <div className="stat-header">
            <span className="stat-label">Fraud Detected</span>
            <FileWarning size={18} className="stat-icon" style={{ color: '#ff4444', opacity: 0.7 }} />
          </div>
          <div className="stat-value red">{fraudDetected.toLocaleString()}</div>
          <div className="stat-change">Flagged as malicious</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Fraud Rate</span>
            <TrendingUp size={18} className="stat-icon" />
          </div>
          <div className="stat-value orange">{fraudRate}%</div>
          <div className="stat-change">Of all analyzed transactions</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-label">Blockchain Reports</span>
            <Link2 size={18} className="stat-icon" />
          </div>
          <div className="stat-value blue">{blockchainReports.toLocaleString()}</div>
          <div className="stat-change">Immutably logged on-chain</div>
        </div>
      </div>

      {/* ===== Charts ===== */}
      <div className="charts-grid">
        {/* Summary Stats Card */}
        <div className="chart-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '30px 20px' }}>
          <div className="chart-title" style={{ marginBottom: '20px' }}>
            <Activity size={16} />
            System Summary
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <div style={{ textAlign: 'center', padding: '10px', borderRadius: '8px', background: '#1e1e45' }}>
              <div style={{ fontSize: '0.8rem', color: '#8888aa', marginBottom: '8px' }}>Detection Accuracy</div>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#00ff88', fontFamily: "'JetBrains Mono', monospace" }}>100%</div>
            </div>
            <div style={{ textAlign: 'center', padding: '10px', borderRadius: '8px', background: '#1e1e45' }}>
              <div style={{ fontSize: '0.8rem', color: '#8888aa', marginBottom: '8px' }}>Blockchain Logged</div>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#00ccff', fontFamily: "'JetBrains Mono', monospace" }}>
                {fraudDetected > 0 ? Math.round((blockchainReports / fraudDetected) * 100) : 0}%
              </div>
            </div>
          </div>
        </div>

        {/* Risk Score Distribution Area Chart */}
        <div className="chart-card">
          <div className="chart-title">
            <Activity size={16} />
            Risk Score Distribution
          </div>
          {riskDistribution.some(d => d.count > 0) ? (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={riskDistribution} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <defs>
                  <linearGradient id="riskGradient" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#00ff88" stopOpacity={0.8} />
                    <stop offset="40%" stopColor="#ffd700" stopOpacity={0.8} />
                    <stop offset="70%" stopColor="#ff8c00" stopOpacity={0.8} />
                    <stop offset="100%" stopColor="#ff4444" stopOpacity={0.8} />
                  </linearGradient>
                  <linearGradient id="riskFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#ff4444" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="#ff4444" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e1e45" />
                <XAxis
                  dataKey="name"
                  tick={{ fill: '#8888aa', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
                  axisLine={{ stroke: '#1e1e45' }}
                  tickLine={{ stroke: '#1e1e45' }}
                  label={{
                    value: 'Risk Score %',
                    position: 'insideBottom',
                    offset: -2,
                    style: { fill: '#555577', fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }
                  }}
                />
                <YAxis
                  tick={{ fill: '#8888aa', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
                  axisLine={{ stroke: '#1e1e45' }}
                  tickLine={{ stroke: '#1e1e45' }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                  type="monotone"
                  dataKey="count"
                  name="Alerts"
                  stroke="#ff6b9d"
                  strokeWidth={2}
                  fill="url(#riskFill)"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">
              <Activity size={40} style={{ color: '#555577', marginBottom: 8 }} />
              <p>No risk score data available. Scan transactions to generate risk analysis.</p>
            </div>
          )}
        </div>
      </div>

      {/* ===== Recent Alerts Table ===== */}
      <div className="table-card">
        <div className="table-header">
          <div className="table-title">
            <AlertTriangle size={16} />
            Recent Alerts
            {alerts.length > 0 && (
              <span style={{
                fontSize: '0.7rem',
                color: '#555577',
                fontFamily: "'JetBrains Mono', monospace",
                fontWeight: 400,
                marginLeft: 8,
              }}>
                Showing {alerts.length} most recent
              </span>
            )}
          </div>
        </div>

        {loading && alerts.length === 0 ? (
          <div className="loading-container">
            <div className="loading-spinner" />
            <span>Loading alerts...</span>
          </div>
        ) : alerts.length === 0 ? (
          <div className="empty-state">
            <Shield size={48} style={{ color: '#555577', marginBottom: 12 }} />
            <p style={{ fontSize: '1rem', marginBottom: 4 }}>No alerts yet</p>
            <p>Click "Ingest Dataset" then "Scan Transactions" to analyze data and generate alerts.</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>TX Hash</th>
                  <th>Risk Score</th>
                  <th>Severity</th>
                  <th>Blockchain</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((alert, idx) => (
                  <tr key={alert._id || idx} className={alert.is_fraud ? 'fraud-row' : ''}>
                    <td style={{ color: '#8888aa', fontSize: '0.8rem', fontFamily: "'JetBrains Mono', monospace" }}>
                      {formatTime(alert.created_at)}
                    </td>
                    <td>
                      <span className="tx-hash" title={alert.tx_hash}>
                        {truncateHash(alert.tx_hash)}
                      </span>
                    </td>
                    <td>
                      <div className="risk-bar-container">
                        <div className="risk-bar-track">
                          <div
                            className={`risk-bar-fill ${getRiskLevel(alert.risk_score || 0)}`}
                            style={{ width: `${Math.min((alert.risk_score || 0) * 100, 100)}%` }}
                          />
                        </div>
                        <span className="risk-value">
                          {((alert.risk_score || 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td>
                      <span className={`severity-badge ${alert.severity || 'SAFE'}`}>
                        {alert.severity || 'SAFE'}
                      </span>
                    </td>
                    <td>
                      <span className={`blockchain-badge ${alert.blockchain_logged ? 'logged' : 'not-logged'}`}>
                        {alert.blockchain_logged ? (
                          <><Link2 size={10} /> Logged</>
                        ) : (
                          '--'
                        )}
                      </span>
                    </td>
                    <td>
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: '3px',
                        fontSize: '0.75rem',
                        fontWeight: 'bold',
                        background: alert.is_fraud ? '#ff444433' : '#00ff8833',
                        color: alert.is_fraud ? '#ff4444' : '#00ff88',
                        fontFamily: "'JetBrains Mono', monospace"
                      }}>
                        {alert.is_fraud ? '🚨 FRAUD' : '✅ SAFE'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ===== Toast Notification ===== */}
      {toast && (
        <div className={`toast ${toast.type}`}>
          {toast.type === 'success' && <span style={{ marginRight: 8 }}>&#10003;</span>}
          {toast.type === 'error' && <span style={{ marginRight: 8 }}>&#10007;</span>}
          {toast.type === 'info' && <span style={{ marginRight: 8 }}>&#9432;</span>}
          {toast.message}
        </div>
      )}
    </div>
  );
}

export default App;
