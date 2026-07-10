'use client';

import { useState, useEffect } from 'react';

export default function HealthPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const check = async () => {
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/health`);
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (e: any) {
      setError(e.message || 'API Offline');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    check();
  }, []);

  return (
    <div style={{ padding: '3rem 2rem', maxWidth: '800px', margin: '0 auto' }}>
      <div className="glass-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
          <h1 style={{ background: 'linear-gradient(to right, #fff, var(--primary))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', fontSize: '2rem' }}>
            System Diagnostics Explorer
          </h1>
          <a href="/" className="btn btn-secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}>
            Back to Dashboard
          </a>
        </div>
        
        <button onClick={check} className="btn btn-primary" style={{ marginBottom: '2rem' }} disabled={loading}>
          {loading ? 'Refreshing Diagnostics...' : 'Re-Run Diagnostics'}
        </button>

        {error && (
          <div style={{ border: '1px solid var(--error)', padding: '1rem', borderRadius: '0.5rem', background: 'var(--error-glow)', color: 'var(--error)', marginBottom: '1rem', fontFamily: 'var(--font-mono)' }}>
            Error: {error}
          </div>
        )}

        {data && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', background: 'rgba(255,255,255,0.02)', padding: '1.25rem', borderRadius: '0.5rem', border: '1px solid var(--card-border)' }}>
              <div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Overall Status</div>
                <span className={`status-badge ${data.status === 'healthy' ? 'healthy' : 'degraded'}`} style={{ marginTop: '0.25rem' }}>
                  <span className="status-dot"></span>{data.status.toUpperCase()}
                </span>
              </div>
              <div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Environment</div>
                <code style={{ color: 'var(--primary)', fontWeight: 600 }}>{data.environment}</code>
              </div>
              <div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Project Name</div>
                <div style={{ fontWeight: 600 }}>{data.project}</div>
              </div>
              <div>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>API Version</div>
                <code>{data.version}</code>
              </div>
            </div>

            <div style={{ borderTop: '1px solid var(--card-border)', paddingTop: '1.5rem' }}>
              <h3 style={{ fontSize: '1.25rem', color: '#fff', marginBottom: '1rem' }}>Database Subsystem Health</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>DB Status</div>
                  <span className={`status-badge ${data.database.status === 'healthy' ? 'healthy' : 'unhealthy'}`} style={{ marginTop: '0.25rem' }}>
                    <span className="status-dot"></span>{data.database.status}
                  </span>
                </div>
                <div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Query Latency</div>
                  <code style={{ fontSize: '1.1rem', color: 'var(--accent)' }}>{data.database.latency_ms} ms</code>
                </div>
              </div>
              {data.database.error && (
                <div style={{ border: '1px solid var(--error)', padding: '1rem', borderRadius: '0.5rem', background: 'var(--error-glow)', color: 'var(--error)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                  <strong>Exception:</strong> {data.database.error}
                </div>
              )}
            </div>

            <div style={{ borderTop: '1px solid var(--card-border)', paddingTop: '1.5rem' }}>
              <h3 style={{ fontSize: '1.25rem', color: '#fff', marginBottom: '1rem' }}>Raw JSON Response Payload</h3>
              <pre style={{ background: '#111827', padding: '1rem', borderRadius: '0.5rem', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: '#00f0ff', overflowX: 'auto', border: '1px solid rgba(255,255,255,0.05)' }}>
                {JSON.stringify(data, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
