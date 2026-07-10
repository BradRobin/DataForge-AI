'use client';

import { useState, useEffect } from 'react';

interface HealthData {
  status: string;
  environment: string;
  project: string;
  version: string;
  database: {
    status: string;
    latency_ms: number;
    error: string | null;
  };
}

export default function Home() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const res = await fetch(`${apiUrl}/health`);
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const data = await res.json();
      setHealth(data);
      setError(null);
    } catch (e: any) {
      setHealth(null);
      setError(e.message || 'Could not connect to FastAPI Backend.');
    } finally {
      setLoading(false);
      setLastUpdated(new Date());
    }
  };

  useEffect(() => {
    fetchHealth();
    // Poll every 10 seconds for real-time status update
    const interval = setInterval(fetchHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  const getBackendStatus = () => {
    if (loading && !health && !error) return { label: 'Checking...', class: 'degraded' };
    if (error) return { label: 'Offline', class: 'unhealthy' };
    if (health) {
      if (health.status === 'healthy') return { label: 'Online', class: 'healthy' };
      if (health.status === 'degraded') return { label: 'Degraded', class: 'degraded' };
    }
    return { label: 'Offline', class: 'unhealthy' };
  };

  const getDbStatus = () => {
    if (loading && !health && !error) return { label: 'Checking...', class: 'degraded' };
    if (error) return { label: 'Unknown', class: 'unhealthy' };
    if (health && health.database) {
      if (health.database.status === 'healthy') return { label: 'Connected', class: 'healthy' };
      return { label: 'Disconnected', class: 'unhealthy' };
    }
    return { label: 'Disconnected', class: 'unhealthy' };
  };

  const backendStatus = getBackendStatus();
  const dbStatus = getDbStatus();

  return (
    <>
      <header className="header">
        <div className="container header-content">
          <div className="logo-container">
            <div className="logo-icon">DF</div>
            <div className="logo-text">DataForge AI</div>
            <div className="logo-tagline">Phase 1</div>
          </div>
          <div>
            <span className={`status-badge ${backendStatus.class}`} id="backend-status-badge">
              <span className="status-dot"></span>
              Backend API: {backendStatus.label}
            </span>
          </div>
        </div>
      </header>

      <main className="container" style={{ padding: '3rem 2rem 5rem 2rem', flex: 1 }}>
        {/* Hero Section */}
        <section style={{ marginBottom: '4rem', textAlign: 'center' }}>
          <h1 style={{ fontSize: '3rem', fontWeight: 800, marginBottom: '1rem', background: 'linear-gradient(to right, #ffffff, #a5b4fc, #00f0ff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            AI Data Engineering Pipeline
          </h1>
          <p style={{ fontSize: '1.2rem', maxWidth: '700px', margin: '0 auto 2.5rem auto' }}>
            Production-ready foundation for collecting, cleaning, normalizing, deduplicating, and exporting high-quality training and evaluation datasets.
          </p>
          
          {/* Quick Stats Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', maxWidth: '900px', margin: '0 auto' }}>
            {/* Backend Health Card */}
            <div className={`glass-card ${backendStatus.class === 'healthy' ? 'primary-active' : ''}`} style={{ textAlign: 'left' }}>
              <h3 style={{ fontSize: '1.1rem', color: 'var(--text-secondary)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Backend Status</h3>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '2rem', fontWeight: 800 }}>{backendStatus.label}</span>
                <span className={`status-badge ${backendStatus.class}`} style={{ padding: '0.2rem' }}>
                  <span className="status-dot"></span>
                </span>
              </div>
              <p style={{ fontSize: '0.85rem' }}>
                URL: <code>{process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}</code>
              </p>
              {health && (
                <div style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  Env: <strong>{health.environment}</strong> | Version: <strong>{health.version}</strong>
                </div>
              )}
            </div>

            {/* DB Health Card */}
            <div className={`glass-card ${dbStatus.class === 'healthy' ? 'accent-active' : ''}`} style={{ textAlign: 'left' }}>
              <h3 style={{ fontSize: '1.1rem', color: 'var(--text-secondary)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>PostgreSQL Database</h3>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '2rem', fontWeight: 800 }}>{dbStatus.label}</span>
                <span className={`status-badge ${dbStatus.class}`} style={{ padding: '0.2rem' }}>
                  <span className="status-dot"></span>
                </span>
              </div>
              {health && health.database ? (
                <div>
                  <p style={{ fontSize: '0.85rem' }}>
                    Latency: <strong>{health.database.latency_ms} ms</strong>
                  </p>
                  {health.database.error && (
                    <p style={{ fontSize: '0.8rem', color: 'var(--error)', marginTop: '0.5rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={health.database.error}>
                      Error: {health.database.error}
                    </p>
                  )}
                </div>
              ) : (
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  {error ? 'Connection failed - backend offline' : 'Checking database status...'}
                </p>
              )}
            </div>
          </div>
        </section>

        {/* Pipeline Architecture Title */}
        <section>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--card-border)', paddingBottom: '1rem', marginBottom: '2rem' }}>
            <div>
              <h2 style={{ fontSize: '1.75rem', color: '#ffffff' }}>Pipeline Modular Folder Architecture</h2>
              <p style={{ fontSize: '0.95rem', marginTop: '0.25rem' }}>These isolated modules structure our data flow, fully scaffolded for Phase 2.</p>
            </div>
            <button onClick={fetchHealth} className="btn btn-secondary" style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }} disabled={loading}>
              {loading ? 'Refreshing...' : 'Refresh Health'}
            </button>
          </div>

          {/* Diagnostic Warning Box when Database/API is down */}
          {error && (
            <div className="glass-card" style={{ border: '1px solid var(--error)', backgroundColor: 'rgba(239, 68, 68, 0.05)', marginBottom: '3rem', padding: '1.5rem' }}>
              <h4 style={{ color: 'var(--error)', fontSize: '1.1rem', marginBottom: '0.5rem' }}>⚠️ Connection Diagnostic Warning</h4>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                The Next.js frontend is running, but it cannot reach the FastAPI backend at <code>http://localhost:8000</code>. 
                Please ensure the backend is started by running:
              </p>
              <pre style={{ background: '#111827', padding: '0.75rem', borderRadius: '0.5rem', marginTop: '0.75rem', fontSize: '0.85rem', fontFamily: 'var(--font-mono)', border: '1px solid rgba(255,255,255,0.05)', overflowX: 'auto', color: '#00f0ff' }}>
                python -m poetry run uvicorn app.main:app --reload
              </pre>
            </div>
          )}

          {health && health.database.status === 'unhealthy' && (
            <div className="glass-card" style={{ border: '1px solid var(--warning)', backgroundColor: 'rgba(245, 158, 11, 0.05)', marginBottom: '3rem', padding: '1.5rem' }}>
              <h4 style={{ color: 'var(--warning)', fontSize: '1.1rem', marginBottom: '0.5rem' }}>⚠️ Database Fallback Notice</h4>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                The FastAPI backend is online, but it cannot connect to the PostgreSQL database server.
                The health status is currently <strong>degraded</strong>. 
                If you want to run the backend locally without PostgreSQL installed, uncomment the SQLite fallback line in your <code>.env</code> file:
              </p>
              <pre style={{ background: '#111827', padding: '0.75rem', borderRadius: '0.5rem', marginTop: '0.75rem', fontSize: '0.85rem', fontFamily: 'var(--font-mono)', border: '1px solid rgba(255,255,255,0.05)', color: '#bd00ff' }}>
                DATABASE_URL="sqlite+aiosqlite:///./dataforge.db"
              </pre>
            </div>
          )}

          {/* Pipeline Cards Grid */}
          <div className="pipeline-grid">
            {/* Step 1 */}
            <div className="glass-card">
              <div className="pipeline-step-header">
                <span className="step-num">MODULE 01</span>
                <span className="status-badge healthy"><span className="status-dot"></span>Ready</span>
              </div>
              <h3 className="step-title">Ingest</h3>
              <p style={{ fontSize: '0.95rem' }}>
                Collects raw public text data from web crawlers, API feeds, and raw file uploads. Handles rate limiting, authentication, and source metadata tagging.
              </p>
              <div style={{ marginTop: '1.5rem', fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                Folder: backend/app/features/ingest/
              </div>
            </div>

            {/* Step 2 */}
            <div className="glass-card">
              <div className="pipeline-step-header">
                <span className="step-num">MODULE 02</span>
                <span className="status-badge healthy"><span className="status-dot"></span>Ready</span>
              </div>
              <h3 className="step-title">Clean</h3>
              <p style={{ fontSize: '0.95rem' }}>
                Filters boilerplate layout elements, removes HTML/Markdown tags, handles encoding issues, and strips out garbage characters or placeholder texts.
              </p>
              <div style={{ marginTop: '1.5rem', fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                Folder: backend/app/features/clean/
              </div>
            </div>

            {/* Step 3 */}
            <div className="glass-card">
              <div className="pipeline-step-header">
                <span className="step-num">MODULE 03</span>
                <span className="status-badge healthy"><span className="status-dot"></span>Ready</span>
              </div>
              <h3 className="step-title">Normalize</h3>
              <p style={{ fontSize: '0.95rem' }}>
                Standardizes whitespace, unifies unicode formats, converts character casings if required, and restructures text chunks to ready them for modeling.
              </p>
              <div style={{ marginTop: '1.5rem', fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                Folder: backend/app/features/normalize/
              </div>
            </div>

            {/* Step 4 */}
            <div className="glass-card">
              <div className="pipeline-step-header">
                <span className="step-num">MODULE 04</span>
                <span className="status-badge healthy"><span className="status-dot"></span>Ready</span>
              </div>
              <h3 className="step-title">Deduplicate</h3>
              <p style={{ fontSize: '0.95rem' }}>
                Filters exact duplicate documents and applies fuzzy deduplication using MinHash LSH (Locality Sensitive Hashing) to discard near-identical texts.
              </p>
              <div style={{ marginTop: '1.5rem', fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                Folder: backend/app/features/deduplicate/
              </div>
            </div>

            {/* Step 5 */}
            <div className="glass-card">
              <div className="pipeline-step-header">
                <span className="step-num">MODULE 05</span>
                <span className="status-badge healthy"><span className="status-dot"></span>Ready</span>
              </div>
              <h3 className="step-title">Analyze</h3>
              <p style={{ fontSize: '0.95rem' }}>
                Runs analytical models to calculate perplexity score, counts token sizes, classifies toxicity/bias levels, and computes quality indices.
              </p>
              <div style={{ marginTop: '1.5rem', fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                Folder: backend/app/features/analyze/
              </div>
            </div>

            {/* Step 6 */}
            <div className="glass-card">
              <div className="pipeline-step-header">
                <span className="step-num">MODULE 06</span>
                <span className="status-badge healthy"><span className="status-dot"></span>Ready</span>
              </div>
              <h3 className="step-title">Export</h3>
              <p style={{ fontSize: '0.95rem' }}>
                Packages the cleaned, deduplicated, and validated data into custom formats like JSONL, Parquet, or CSV, optimized for AI model ingestion.
              </p>
              <div style={{ marginTop: '1.5rem', fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                Folder: backend/app/features/export/
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="container footer-content">
          <div>
            &copy; 2026 <strong>DataForge AI</strong>. All rights reserved.
          </div>
          <div className="footer-links">
            <a href="/docs" className="footer-link">API Docs</a>
            <a href="https://github.com" className="footer-link" target="_blank" rel="noopener noreferrer">GitHub</a>
          </div>
        </div>
      </footer>
    </>
  );
}
