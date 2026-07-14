'use client';

import { useState, useEffect } from 'react';

// Interfaces for Backend REST Contracts
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

interface AnalyticsOverview {
  total_documents: number;
  unique_documents: number;
  duplicate_documents: number;
  duplicate_rate: number;
  length_stats: {
    avg_word_count: number;
    median_word_count: number;
    avg_char_count: number;
    median_char_count: number;
  };
  language_distribution: Record<string, number>;
  source_distribution: Record<string, number>;
  quality_stats: {
    avg_score: number;
    median_score: number;
    min_score: number;
    max_score: number;
    buckets: Record<string, number>;
  };
  top_keywords: Array<{ word: string; frequency: number }>;
  collection_timeline: Record<string, number>;
}

interface SandboxCleanResult {
  original_text: string;
  cleaned_text: string;
}

interface SandboxQualityResult {
  quality_score: number;
  sub_scores: {
    length_score: number;
    stop_word_score: number;
    readability_score: number;
    noise_score: number;
    repetition_score: number;
    malformed_score: number;
  };
  metrics: {
    word_count: number;
    char_count: number;
    stop_word_density: number;
    noise_ratio: number;
    repetition_ratio: number;
    malformed_word_ratio: number;
  };
}

interface IngestJobStatus {
  job_id: string;
  status: string;
  url_count: number;
  collected_count: number;
  errors: string[];
  started_at: string;
  completed_at: string | null;
}

export default function Home() {
  // Navigation tab state
  const [activeTab, setActiveTab] = useState<string>('overview');

  // API/DB connection health states
  const [health, setHealth] = useState<HealthData | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);

  // Analytics Overview states
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState<boolean>(true);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);

  // 1. Ingestion Form states
  const [seedUrls, setSeedUrls] = useState<string>('https://raw.githubusercontent.com/google/flatbuffers/master/README.md');
  const [collectorType, setCollectorType] = useState<string>('http');
  const [activeJobs, setActiveJobs] = useState<Record<string, IngestJobStatus>>({});
  const [ingestTriggering, setIngestTriggering] = useState<boolean>(false);
  const [ingestMessage, setIngestMessage] = useState<string | null>(null);

  // 2. Data Cleaning states
  const [sandboxCleanRawText, setSandboxCleanRawText] = useState<string>('<html><body><header>Nav Links</header><h1>Hello &amp; Welcome!</h1><p>This is standard clean text mixed with double-encoded chars like Ã© and ads.</p><footer>Cookies and copyrights</footer></body></html>');
  const [sandboxCleanResult, setSandboxCleanResult] = useState<SandboxCleanResult | null>(null);
  const [sandboxCleanLoading, setSandboxCleanLoading] = useState<boolean>(false);
  const [batchCleanMessage, setBatchCleanMessage] = useState<string | null>(null);
  const [batchCleanLoading, setBatchCleanLoading] = useState<boolean>(false);

  // 3. Deduplication states
  const [dedupThreshold, setDedupThreshold] = useState<number>(12);
  const [dedupLoading, setDedupLoading] = useState<boolean>(false);
  const [dedupMessage, setDedupMessage] = useState<string | null>(null);

  // 4. Quality Grading states
  const [sandboxQualityRawText, setSandboxQualityRawText] = useState<string>('This is a high quality sample document with a significant density of common English stop words to ensure a high language confidence. It features structured sentence structures, proper casing, and uses vocabulary in correct contexts to achieve high overall quality rating scores.');
  const [sandboxQualityResult, setSandboxQualityResult] = useState<SandboxQualityResult | null>(null);
  const [sandboxQualityLoading, setSandboxQualityLoading] = useState<boolean>(false);
  const [batchQualityMessage, setBatchQualityMessage] = useState<string | null>(null);
  const [batchQualityLoading, setBatchQualityLoading] = useState<boolean>(false);

  // 5. Dataset Export states
  const [exportFormat, setExportFormat] = useState<string>('csv');
  const [exportSource, setExportSource] = useState<string>('');
  const [exportLanguage, setExportLanguage] = useState<string>('');
  const [exportMinQuality, setExportMinQuality] = useState<number>(0);
  const [exportExcludeDuplicates, setExportExcludeDuplicates] = useState<boolean>(false);
  const [exportMessage, setExportMessage] = useState<string | null>(null);
  const [exportLoading, setExportLoading] = useState<boolean>(false);

  // 6. One-Click Pipeline states
  const [pipelineUrls, setPipelineUrls] = useState<string>('https://raw.githubusercontent.com/google/flatbuffers/master/README.md');
  const [pipelineFormat, setPipelineFormat] = useState<string>('parquet');
  const [pipelineThreshold, setPipelineThreshold] = useState<number>(12);
  const [pipelineJobId, setPipelineJobId] = useState<string | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<any | null>(null);
  const [pipelineRunning, setPipelineRunning] = useState<boolean>(false);
  const [pipelineMessage, setPipelineMessage] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Fetch health check
  const fetchHealth = async () => {
    setHealthLoading(true);
    try {
      const res = await fetch(`${apiUrl}/health`);
      if (!res.ok) throw new Error(`Status: ${res.status}`);
      const data = await res.json();
      setHealth(data);
      setHealthError(null);
    } catch (e: any) {
      setHealth(null);
      setHealthError(e.message || 'Could not connect to backend.');
    } finally {
      setHealthLoading(false);
    }
  };

  // Fetch dataset analytics overview
  const fetchAnalytics = async () => {
    setAnalyticsLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/v1/analytics/overview`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setAnalytics(data);
      setAnalyticsError(null);
    } catch (e: any) {
      setAnalytics(null);
      setAnalyticsError(e.message || 'Failed to fetch analytics metrics.');
    } finally {
      setAnalyticsLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    fetchAnalytics();
    
    // Poll health and analytics every 15 seconds
    const interval = setInterval(() => {
      fetchHealth();
      fetchAnalytics();
    }, 15000);
    
    return () => clearInterval(interval);
  }, []);

  // Poll Ingestion Job status
  const pollJobStatus = async (jobId: string) => {
    let pollId: any = null;
    const checkJob = async () => {
      try {
        const res = await fetch(`${apiUrl}/api/v1/ingest/status/${jobId}`);
        if (!res.ok) return;
        const statusData: IngestJobStatus = await res.json();
        
        setActiveJobs(prev => ({
          ...prev,
          [jobId]: statusData
        }));

        if (statusData.status === 'completed' || statusData.status === 'failed') {
          if (pollId) clearInterval(pollId);
          fetchAnalytics(); // Refresh overview counts
        }
      } catch (e) {
        // Suppress background poll errors
      }
    };
    
    await checkJob();
    pollId = setInterval(checkJob, 2000);
  };

  // Trigger ingestion job
  const handleTriggerIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    setIngestTriggering(true);
    setIngestMessage(null);
    try {
      const urlsArray = seedUrls.split('\n').map(u => u.trim()).filter(u => u !== '');
      if (urlsArray.length === 0) {
        throw new Error('Please input at least one URL.');
      }

      const res = await fetch(`${apiUrl}/api/v1/ingest/trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          urls: urlsArray,
          collector_type: collectorType
        })
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Failed to schedule ingestion job.');
      }

      const data = await res.json();
      const jobId = data.job_id;
      setIngestMessage(`Job scheduled successfully! UUID: ${jobId}`);
      
      // Start polling
      pollJobStatus(jobId);
    } catch (e: any) {
      setIngestMessage(`Error: ${e.message}`);
    } finally {
      setIngestTriggering(false);
    }
  };

  // Run Sandbox Cleaning
  const handleSandboxClean = async () => {
    setSandboxCleanLoading(true);
    setSandboxCleanResult(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/clean/text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: sandboxCleanRawText })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setSandboxCleanResult(data);
    } catch (e: any) {
      alert(`Error cleaning text: ${e.message}`);
    } finally {
      setSandboxCleanLoading(false);
    }
  };

  // Run Batch Cleaning
  const handleBatchClean = async () => {
    setBatchCleanLoading(true);
    setBatchCleanMessage(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/clean/batch/run`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setBatchCleanMessage(`Batch cleaning complete! Processed ${data.processed_count} documents.`);
      fetchAnalytics(); // Refresh statistics
    } catch (e: any) {
      setBatchCleanMessage(`Error: ${e.message}`);
    } finally {
      setBatchCleanLoading(false);
    }
  };

  // Run Deduplication Engine
  const handleRunDeduplication = async () => {
    setDedupLoading(true);
    setDedupMessage(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/dedup/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ threshold: dedupThreshold })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setDedupMessage(`Deduplication complete! Total Checked: ${data.total_checked}. Exact duplicates: ${data.exact_duplicates_found}. Near duplicates: ${data.near_duplicates_found}.`);
      fetchAnalytics();
    } catch (e: any) {
      setDedupMessage(`Error: ${e.message}`);
    } finally {
      setDedupLoading(false);
    }
  };

  // Run Sandbox Quality Evaluation
  const handleSandboxQuality = async () => {
    setSandboxQualityLoading(true);
    setSandboxQualityResult(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/quality/text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: sandboxQualityRawText })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setSandboxQualityResult(data);
    } catch (e: any) {
      alert(`Error evaluating quality: ${e.message}`);
    } finally {
      setSandboxQualityLoading(false);
    }
  };

  // Run Batch Quality Evaluation
  const handleBatchQuality = async () => {
    setBatchQualityLoading(true);
    setBatchQualityMessage(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/quality/batch/run`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setBatchQualityMessage(`Batch quality evaluation complete! Scored ${data.processed_count} documents.`);
      fetchAnalytics();
    } catch (e: any) {
      setBatchQualityMessage(`Error: ${e.message}`);
    } finally {
      setBatchQualityLoading(false);
    }
  };

  // Download Dataset Export File
  const handleDownloadExport = async () => {
    setExportLoading(true);
    setExportMessage(null);
    try {
      const params = new URLSearchParams();
      params.append('format', exportFormat);
      if (exportSource) params.append('source', exportSource);
      if (exportLanguage) params.append('language', exportLanguage);
      if (exportMinQuality > 0) params.append('min_quality', exportMinQuality.toString());
      if (exportExcludeDuplicates) params.append('exclude_duplicates', 'true');

      const downloadUrl = `${apiUrl}/api/v1/export?${params.toString()}`;
      
      const res = await fetch(downloadUrl);
      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Export compilation failed.');
      }

      const blob = await res.blob();
      
      // Extract file name from response headers or assign defaults
      let filename = `dataset_export.${exportFormat}`;
      const disposition = res.headers.get('content-disposition');
      if (disposition && disposition.includes('filename=')) {
        const match = disposition.match(/filename="(.+?)"/);
        if (match && match[1]) filename = match[1];
      }

      // Create download link in DOM
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      
      setExportMessage(`Download complete: ${filename}`);
    } catch (e: any) {
      setExportMessage(`Error: ${e.message}`);
    } finally {
      setExportLoading(false);
    }
  };

  // Trigger & Poll One-Click Pipeline
  const handleTriggerPipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    setPipelineRunning(true);
    setPipelineJobId(null);
    setPipelineStatus(null);
    setPipelineMessage(null);
    try {
      const urlsArray = pipelineUrls.split('\n').map(u => u.trim()).filter(u => u !== '');
      if (urlsArray.length === 0) {
        throw new Error('Please input at least one URL.');
      }

      const res = await fetch(`${apiUrl}/api/v1/pipeline/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          urls: urlsArray,
          threshold: pipelineThreshold,
          export_format: pipelineFormat
        })
      });

      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Failed to trigger pipeline orchestrator.');
      }

      const data = await res.json();
      const pid = data.pipeline_id;
      setPipelineJobId(pid);
      setPipelineMessage(`Pipeline job accepted: ${pid}`);
      
      // Start polling pipeline status
      pollPipelineStatus(pid);
    } catch (e: any) {
      setPipelineMessage(`Error: ${e.message}`);
      setPipelineRunning(false);
    }
  };

  const pollPipelineStatus = async (pid: string) => {
    let pollId: any = null;
    const checkStatus = async () => {
      try {
        const res = await fetch(`${apiUrl}/api/v1/pipeline/status/${pid}`);
        if (!res.ok) return;
        const statusData = await res.json();
        setPipelineStatus(statusData);

        if (statusData.status === 'completed' || statusData.status === 'failed' || statusData.status === 'cancelled') {
          if (pollId) clearInterval(pollId);
          setPipelineRunning(false);
          fetchAnalytics(); // Refresh dashboard counts
          if (statusData.status === 'completed') {
            setPipelineMessage('Pipeline completed successfully! Ready for download.');
          } else if (statusData.status === 'cancelled') {
            setPipelineMessage('Pipeline cancelled by user.');
          } else {
            setPipelineMessage(`Pipeline failed: ${statusData.error}`);
          }
        }
      } catch (e) {
        // Suppress background errors
      }
    };

    await checkStatus();
    pollId = setInterval(checkStatus, 1500);
  };

  const handleCancelPipeline = async () => {
    if (!pipelineJobId) return;
    try {
      const res = await fetch(`${apiUrl}/api/v1/pipeline/cancel/${pipelineJobId}`, {
        method: 'POST'
      });
      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Failed to cancel pipeline.');
      }
      setPipelineMessage('Cancellation request sent.');
    } catch (e: any) {
      setPipelineMessage(`Error cancelling: ${e.message}`);
    }
  };

  const handleDownloadPipelineExport = async () => {
    if (!pipelineJobId) return;
    try {
      const downloadUrl = `${apiUrl}/api/v1/pipeline/download/${pipelineJobId}`;
      const res = await fetch(downloadUrl);
      if (!res.ok) {
        const errJson = await res.json();
        throw new Error(errJson.detail || 'Export download failed.');
      }

      const blob = await res.blob();
      let filename = `pipeline_export.${pipelineFormat}`;
      const disposition = res.headers.get('content-disposition');
      if (disposition && disposition.includes('filename=')) {
        const match = disposition.match(/filename="(.+?)"/);
        if (match && match[1]) filename = match[1];
      }

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      
      setPipelineMessage(`Downloaded package: ${filename}`);
    } catch (e: any) {
      setPipelineMessage(`Error: ${e.message}`);
    }
  };

  // Get status color states
  const getBackendStatus = () => {
    if (healthLoading && !health && !healthError) return { label: 'Checking...', class: 'degraded' };
    if (healthError) return { label: 'Offline', class: 'unhealthy' };
    if (health) {
      if (health.status === 'healthy') return { label: 'Online', class: 'healthy' };
      if (health.status === 'degraded') return { label: 'Degraded', class: 'degraded' };
    }
    return { label: 'Offline', class: 'unhealthy' };
  };

  const getDbStatus = () => {
    if (healthLoading && !health && !healthError) return { label: 'Checking...', class: 'degraded' };
    if (healthError) return { label: 'Unknown', class: 'unhealthy' };
    if (health && health.database) {
      if (health.database.status === 'healthy') return { label: 'Connected', class: 'healthy' };
      return { label: 'Disconnected', class: 'unhealthy' };
    }
    return { label: 'Disconnected', class: 'unhealthy' };
  };

  const backendStatus = getBackendStatus();
  const dbStatus = getDbStatus();

  // SVG Line/Area Timeline Calculator
  const renderTimelineChart = () => {
    if (!analytics || !analytics.collection_timeline || Object.keys(analytics.collection_timeline).length === 0) {
      return (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          No collection timeline metrics available.
        </div>
      );
    }

    const timelineData = Object.entries(analytics.collection_timeline).sort((a, b) => a[0].localeCompare(b[0]));
    const maxVal = Math.max(...timelineData.map(d => d[1]), 5);
    const count = timelineData.length;
    
    // Grid sizes
    const width = 600;
    const height = 180;
    const paddingLeft = 40;
    const paddingRight = 20;
    const paddingTop = 20;
    const paddingBottom = 30;

    const chartWidth = width - paddingLeft - paddingRight;
    const chartHeight = height - paddingTop - paddingBottom;

    // Build line points
    const points = timelineData.map((d, index) => {
      const x = paddingLeft + (count > 1 ? (index / (count - 1)) * chartWidth : chartWidth / 2);
      const y = paddingTop + chartHeight - (d[1] / maxVal) * chartHeight;
      return { x, y, date: d[0], value: d[1] };
    });

    const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
    const areaPath = points.length > 0 
      ? `${linePath} L ${points[points.length - 1].x} ${height - paddingBottom} L ${points[0].x} ${height - paddingBottom} Z`
      : '';

    return (
      <div style={{ position: 'relative' }}>
        <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="auto" style={{ background: 'rgba(255,255,255,0.01)', borderRadius: '0.5rem' }}>
          {/* Y Axis Grid Lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => {
            const y = paddingTop + chartHeight * ratio;
            const val = Math.round(maxVal * (1 - ratio));
            return (
              <g key={idx}>
                <line x1={paddingLeft} y1={y} x2={width - paddingRight} y2={y} stroke="rgba(255,255,255,0.05)" strokeDasharray="3,3" />
                <text x={paddingLeft - 8} y={y + 4} fill="var(--text-muted)" fontSize="9" fontFamily="var(--font-mono)" textAnchor="end">{val}</text>
              </g>
            );
          })}

          {/* Area under the line */}
          {areaPath && (
            <path d={areaPath} fill="url(#area-gradient)" opacity="0.3" />
          )}

          {/* Timeline Line */}
          {linePath && (
            <path d={linePath} fill="none" stroke="var(--primary)" strokeWidth="2.5" />
          )}

          {/* Interactive Data Dots */}
          {points.map((p, i) => (
            <g key={i}>
              <circle cx={p.x} cy={p.y} r="4" fill="var(--bg-base)" stroke="var(--primary)" strokeWidth="2" />
              {/* Value label on top of point */}
              <text x={p.x} y={p.y - 8} fill="#ffffff" fontSize="9" fontWeight="700" fontFamily="var(--font-mono)" textAnchor="middle">{p.value}</text>
              {/* Date label at bottom */}
              <text x={p.x} y={height - 10} fill="var(--text-secondary)" fontSize="9" fontFamily="var(--font-mono)" textAnchor="middle">
                {p.date.split('-').slice(1).join('/')}
              </text>
            </g>
          ))}

          {/* Gradient definitions */}
          <defs>
            <linearGradient id="area-gradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--primary)" />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
            </linearGradient>
          </defs>
        </svg>
      </div>
    );
  };

  return (
    <>
      {/* Top Banner Header */}
      <header className="header">
        <div className="container header-content">
          <div className="logo-container">
            <div className="logo-icon">DF</div>
            <div className="logo-text">DataForge AI</div>
            <div className="logo-tagline">v1.0</div>
          </div>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <span className={`status-badge ${backendStatus.class}`} id="backend-status-badge">
              <span className="status-dot"></span>
              API: {backendStatus.label}
            </span>
            <span className={`status-badge ${dbStatus.class}`} id="db-status-badge">
              <span className="status-dot"></span>
              DB: {dbStatus.label}
            </span>
          </div>
        </div>
      </header>

      <main className="container" style={{ padding: '2rem 2rem 5rem 2rem', flex: 1 }}>
        
        {/* Connection Diagnostics Banner */}
        {healthError && (
          <div className="glass-card" style={{ border: '1px solid var(--error)', backgroundColor: 'rgba(239, 68, 68, 0.05)', marginBottom: '2rem', padding: '1.5rem' }}>
            <h4 style={{ color: 'var(--error)', fontSize: '1.1rem', marginBottom: '0.5rem' }}>⚠️ API Server Offline</h4>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              The frontend cannot reach the API backend at <code>{apiUrl}</code>. Ensure the FastAPI application is running locally.
            </p>
          </div>
        )}

        <div className="dashboard-container">
          
          {/* LEFT SIDEBAR NAVIGATION */}
          <aside className="sidebar-card">
            <h3 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', paddingLeft: '1rem', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
              Pipeline Stages
            </h3>
            
            <button className={`sidebar-nav-btn ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>
              📊 Dashboard Overview
            </button>
            <button className={`sidebar-nav-btn ${activeTab === 'ingest' ? 'active' : ''}`} onClick={() => setActiveTab('ingest')}>
              📥 Ingest & Crawl
            </button>
            <button className={`sidebar-nav-btn ${activeTab === 'clean' ? 'active' : ''}`} onClick={() => setActiveTab('clean')}>
              🧹 Cleaning Sandbox
            </button>
            <button className={`sidebar-nav-btn ${activeTab === 'dedup' ? 'active' : ''}`} onClick={() => setActiveTab('dedup')}>
              🔀 Deduplication
            </button>
            <button className={`sidebar-nav-btn ${activeTab === 'quality' ? 'active' : ''}`} onClick={() => setActiveTab('quality')}>
              🛡️ Quality Grading
            </button>
            <button className={`sidebar-nav-btn ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => setActiveTab('analytics')}>
              📈 Dataset Analytics
            </button>
            <button className={`sidebar-nav-btn ${activeTab === 'export' ? 'active' : ''}`} onClick={() => setActiveTab('export')}>
              📦 Dataset Export
            </button>
            <button className={`sidebar-nav-btn ${activeTab === 'pipeline' ? 'active' : ''}`} onClick={() => setActiveTab('pipeline')}>
              🚀 One-Click Pipeline
            </button>

            <hr style={{ border: 'none', borderTop: '1px solid var(--card-border)', margin: '1rem 0' }} />
            <button onClick={() => { fetchHealth(); fetchAnalytics(); }} className="btn btn-secondary" style={{ padding: '0.5rem', fontSize: '0.85rem' }} disabled={healthLoading || analyticsLoading}>
              🔄 Refresh Statistics
            </button>
          </aside>

          {/* RIGHT CONTENT WORKSPACE */}
          <section className="content-panel">
            
            {/* ==========================================
                TAB: OVERVIEW
                ========================================== */}
            {activeTab === 'overview' && (
              <>
                <div style={{ borderBottom: '1px solid var(--card-border)', paddingBottom: '1rem' }}>
                  <h2 style={{ fontSize: '1.75rem', color: '#ffffff' }}>Dashboard Overview</h2>
                  <p style={{ fontSize: '0.95rem', marginTop: '0.25rem' }}>Real-time statistics of documents currently loaded in the DataForge database.</p>
                </div>

                {/* KPI metrics row */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem' }}>
                  <div className="glass-card" style={{ padding: '1.5rem' }}>
                    <h4 style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Total Documents</h4>
                    <span style={{ fontSize: '2.5rem', fontWeight: 800, color: '#ffffff', display: 'block', margin: '0.5rem 0' }}>
                      {analytics ? analytics.total_documents : 0}
                    </span>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Raw collected records</p>
                  </div>
                  
                  <div className="glass-card" style={{ padding: '1.5rem' }}>
                    <h4 style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Unique Files</h4>
                    <span style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--primary)', display: 'block', margin: '0.5rem 0' }}>
                      {analytics ? analytics.unique_documents : 0}
                    </span>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Excluding duplicates</p>
                  </div>

                  <div className="glass-card" style={{ padding: '1.5rem' }}>
                    <h4 style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Duplicate Rate</h4>
                    <span style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--accent)', display: 'block', margin: '0.5rem 0' }}>
                      {analytics ? `${(analytics.duplicate_rate * 100).toFixed(1)}%` : '0.0%'}
                    </span>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      Duplicates flagged: {analytics ? analytics.duplicate_documents : 0}
                    </p>
                  </div>

                  <div className="glass-card" style={{ padding: '1.5rem' }}>
                    <h4 style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Avg Quality Score</h4>
                    <span style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--success)', display: 'block', margin: '0.5rem 0' }}>
                      {analytics ? analytics.quality_stats.avg_score.toFixed(1) : '0.0'}
                    </span>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      Scale of 0.0 - 100.0
                    </p>
                  </div>
                </div>

                {/* Timeline and Quick Actions */}
                <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '1.5rem' }}>
                  
                  {/* Timeline Chart Container */}
                  <div className="glass-card">
                    <h3 style={{ fontSize: '1.1rem', marginBottom: '1.25rem', color: '#ffffff' }}>Collection Timeline</h3>
                    {renderTimelineChart()}
                  </div>

                  {/* Quick Pipeline Actions */}
                  <div className="glass-card">
                    <h3 style={{ fontSize: '1.1rem', marginBottom: '1.25rem', color: '#ffffff' }}>Pipeline Actions</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                      
                      <div>
                        <h4 style={{ fontSize: '0.9rem', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Deduplication Job</h4>
                        <button onClick={handleRunDeduplication} className="btn btn-primary" style={{ width: '100%', fontSize: '0.9rem', padding: '0.6rem' }} disabled={dedupLoading}>
                          {dedupLoading ? 'Computing SimHash...' : 'Run Near-Duplicate check'}
                        </button>
                      </div>

                      <hr style={{ border: 'none', borderTop: '1px solid var(--card-border)' }} />

                      <div>
                        <h4 style={{ fontSize: '0.9rem', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Batch cleaning</h4>
                        <button onClick={handleBatchClean} className="btn btn-secondary" style={{ width: '100%', fontSize: '0.9rem', padding: '0.6rem' }} disabled={batchCleanLoading}>
                          {batchCleanLoading ? 'Cleaning records...' : 'Run HTML Cleaner'}
                        </button>
                      </div>

                      <div>
                        <h4 style={{ fontSize: '0.9rem', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>Batch quality grading</h4>
                        <button onClick={handleBatchQuality} className="btn btn-secondary" style={{ width: '100%', fontSize: '0.9rem', padding: '0.6rem' }} disabled={batchQualityLoading}>
                          {batchQualityLoading ? 'Evaluating texts...' : 'Run Quality Scorer'}
                        </button>
                      </div>

                    </div>
                  </div>
                </div>
              </>
            )}

            {/* ==========================================
                TAB: INGEST & CRAWL
                ========================================== */}
            {activeTab === 'ingest' && (
              <>
                <div style={{ borderBottom: '1px solid var(--card-border)', paddingBottom: '1rem' }}>
                  <h2 style={{ fontSize: '1.75rem', color: '#ffffff' }}>📥 Ingestion & Web Crawling</h2>
                  <p style={{ fontSize: '0.95rem', marginTop: '0.25rem' }}>Trigger modular collectors to retrieve documents asynchronously.</p>
                </div>

                <div className="glass-card">
                  <form onSubmit={handleTriggerIngest} className="form-card">
                    <div className="field-group">
                      <label htmlFor="seed-urls">Seed URLs (one per line)</label>
                      <textarea id="seed-urls" rows={4} className="input-textarea" value={seedUrls} onChange={(e) => setSeedUrls(e.target.value)} required />
                    </div>

                    <div className="form-row">
                      <div className="field-group">
                        <label htmlFor="collector">Collector Plugin</label>
                        <select id="collector" className="input-select" value={collectorType} onChange={(e) => setCollectorType(e.target.value)}>
                          <option value="http">HTTP Crawler (BaseCollector)</option>
                        </select>
                      </div>
                    </div>

                    <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-start' }} disabled={ingestTriggering}>
                      {ingestTriggering ? 'Triggering...' : 'Start Collection Engine'}
                    </button>
                  </form>

                  {ingestMessage && (
                    <div style={{ marginTop: '1.25rem', padding: '0.75rem 1rem', borderRadius: '0.5rem', background: 'rgba(255,255,255,0.03)', fontSize: '0.9rem', border: '1px solid var(--card-border)', color: 'var(--primary)' }}>
                      {ingestMessage}
                    </div>
                  )}
                </div>

                {/* Active Jobs Monitor */}
                <div className="glass-card">
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1.25rem', color: '#ffffff' }}>Background Collection Jobs</h3>
                  
                  {Object.keys(activeJobs).length === 0 ? (
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem' }}>No active crawling jobs monitored in this session.</p>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                      {Object.values(activeJobs).map((job) => (
                        <div key={job.job_id} className="job-item">
                          <div>
                            <span style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>ID: {job.job_id}</span>
                            <div style={{ fontWeight: 600, fontSize: '0.95rem', marginTop: '0.25rem' }}>
                              Urls to Crawl: {job.url_count} | Collected: <strong style={{ color: 'var(--primary)' }}>{job.collected_count}</strong>
                            </div>
                            {job.errors.length > 0 && (
                              <div style={{ color: 'var(--error)', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                                Errors encountered: {job.errors.join(', ')}
                              </div>
                            )}
                          </div>
                          <div>
                            <span className={`status-badge ${job.status === 'completed' ? 'healthy' : job.status === 'failed' ? 'unhealthy' : 'degraded'}`}>
                              <span className="status-dot"></span>
                              {job.status.toUpperCase()}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </>
            )}

            {/* ==========================================
                TAB: CLEANING SANDBOX
                ========================================== */}
            {activeTab === 'clean' && (
              <>
                <div style={{ borderBottom: '1px solid var(--card-border)', paddingBottom: '1rem' }}>
                  <h2 style={{ fontSize: '1.75rem', color: '#ffffff' }}>🧹 Data Cleaning & Normalization</h2>
                  <p style={{ fontSize: '0.95rem', marginTop: '0.25rem' }}>Filter advertising text, cookie banners, navigation menus, and repair encodings.</p>
                </div>

                <div className="glass-card">
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1.25rem', color: '#ffffff' }}>Sandbox Testing</h3>
                  
                  <div className="form-card">
                    <div className="field-group">
                      <label htmlFor="raw-html">Input Text / Raw HTML Markup</label>
                      <textarea id="raw-html" rows={5} className="input-textarea" value={sandboxCleanRawText} onChange={(e) => setSandboxCleanRawText(e.target.value)} />
                    </div>
                    
                    <button onClick={handleSandboxClean} className="btn btn-primary" style={{ alignSelf: 'flex-start' }} disabled={sandboxCleanLoading}>
                      {sandboxCleanLoading ? 'Processing Cleaner...' : 'Test Clean Pipeline'}
                    </button>
                  </div>

                  {sandboxCleanResult && (
                    <div className="sandbox-box" style={{ marginTop: '2rem' }}>
                      <div>
                        <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Original Preview</h4>
                        <div style={{ background: '#111827', padding: '1rem', borderRadius: '0.5rem', minHeight: '150px', maxHeight: '250px', overflowY: 'auto', fontSize: '0.9rem', border: '1px solid var(--card-border)', whiteSpace: 'pre-wrap' }}>
                          {sandboxCleanResult.original_text}
                        </div>
                      </div>

                      <div>
                        <h4 style={{ fontSize: '0.85rem', color: 'var(--primary)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Cleaned Output</h4>
                        <div style={{ background: 'rgba(0, 240, 255, 0.02)', padding: '1rem', borderRadius: '0.5rem', minHeight: '150px', maxHeight: '250px', overflowY: 'auto', fontSize: '0.9rem', border: '1px solid var(--primary-border)', whiteSpace: 'pre-wrap', color: 'var(--text-primary)' }}>
                          {sandboxCleanResult.cleaned_text}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="glass-card">
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '0.5rem', color: '#ffffff' }}>Run Database Cleaning Pipeline</h3>
                  <p style={{ fontSize: '0.9rem', marginBottom: '1.25rem' }}>This evaluates all unscored/uncleaned records inside the database, executing cleanup on raw texts and saving the outputs.</p>
                  
                  <button onClick={handleBatchClean} className="btn btn-secondary" disabled={batchCleanLoading}>
                    {batchCleanLoading ? 'Running...' : 'Run Batch Cleaning Job'}
                  </button>

                  {batchCleanMessage && (
                    <div style={{ marginTop: '1rem', padding: '0.75rem 1rem', borderRadius: '0.5rem', background: 'rgba(255,255,255,0.03)', fontSize: '0.9rem', color: 'var(--success)', border: '1px solid var(--card-border)' }}>
                      {batchCleanMessage}
                    </div>
                  )}
                </div>
              </>
            )}

            {/* ==========================================
                TAB: DEDUPLICATION
                ========================================== */}
            {activeTab === 'dedup' && (
              <>
                <div style={{ borderBottom: '1px solid var(--card-border)', paddingBottom: '1rem' }}>
                  <h2 style={{ fontSize: '1.75rem', color: '#ffffff' }}>🔀 SimHash Deduplication Engine</h2>
                  <p style={{ fontSize: '0.95rem', marginTop: '0.25rem' }}>Compute 64-bit fingerprint shingling and exclude redundant near-duplicates.</p>
                </div>

                <div className="glass-card">
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1.25rem', color: '#ffffff' }}>Configure & Run Deduplication</h3>
                  
                  <div className="form-card">
                    <div className="field-group">
                      <label htmlFor="hamming-threshold">Hamming Distance Similarity Threshold: {dedupThreshold}</label>
                      <input id="hamming-threshold" type="range" min={3} max={25} step={1} className="input-text" style={{ padding: '0.25rem' }} value={dedupThreshold} onChange={(e) => setDedupThreshold(parseInt(e.target.value))} />
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                        SimHash distance of 12 or less identifies near-duplicate texts. A lower threshold is more conservative.
                      </p>
                    </div>

                    <button onClick={handleRunDeduplication} className="btn btn-primary" style={{ alignSelf: 'flex-start' }} disabled={dedupLoading}>
                      {dedupLoading ? 'Computing Hamming Vectors...' : 'Execute Deduplication Job'}
                    </button>
                  </div>

                  {dedupMessage && (
                    <div style={{ marginTop: '1.25rem', padding: '0.75rem 1rem', borderRadius: '0.5rem', background: 'rgba(255,255,255,0.03)', fontSize: '0.9rem', color: 'var(--primary)', border: '1px solid var(--card-border)' }}>
                      {dedupMessage}
                    </div>
                  )}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                  <div className="glass-card">
                    <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#ffffff' }}>Exact Hash Matching</h3>
                    <p style={{ fontSize: '0.95rem' }}>
                      DataForge generates SHA-256 signatures automatically upon doc creation. Endpoints flag duplicate text immediately on DB insertion.
                    </p>
                  </div>

                  <div className="glass-card">
                    <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#ffffff' }}>Near-Duplicate (SimHash)</h3>
                    <p style={{ fontSize: '0.95rem' }}>
                      Character 3-grams shingling maps high-dimensional text to 64-bit fingers, ensuring robust detection for slight paraphrasing or boilerplate modifications.
                    </p>
                  </div>
                </div>
              </>
            )}

            {/* ==========================================
                TAB: QUALITY GRADING
                ========================================== */}
            {activeTab === 'quality' && (
              <>
                <div style={{ borderBottom: '1px solid var(--card-border)', paddingBottom: '1rem' }}>
                  <h2 style={{ fontSize: '1.75rem', color: '#ffffff' }}>🛡️ Document Quality Scoring</h2>
                  <p style={{ fontSize: '0.95rem', marginTop: '0.25rem' }}>Grade document metrics based on readability, spelling noise, repetitions, and text constraints.</p>
                </div>

                <div className="glass-card">
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1.25rem', color: '#ffffff' }}>Sandbox Testing</h3>
                  
                  <div className="form-card">
                    <div className="field-group">
                      <label htmlFor="quality-raw">Input Text to Grade</label>
                      <textarea id="quality-raw" rows={4} className="input-textarea" value={sandboxQualityRawText} onChange={(e) => setSandboxQualityRawText(e.target.value)} />
                    </div>

                    <button onClick={handleSandboxQuality} className="btn btn-primary" style={{ alignSelf: 'flex-start' }} disabled={sandboxQualityLoading}>
                      {sandboxQualityLoading ? 'Evaluating heuristics...' : 'Run Quality Diagnostics'}
                    </button>
                  </div>

                  {sandboxQualityResult && (
                    <div style={{ marginTop: '2rem', borderTop: '1px solid var(--card-border)', paddingTop: '1.5rem' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', marginBottom: '1.5rem' }}>
                        <div>
                          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Composite Grade</span>
                          <span style={{ fontSize: '3rem', fontWeight: 800, color: 'var(--success)', display: 'block' }}>
                            {sandboxQualityResult.quality_score.toFixed(1)}
                          </span>
                        </div>
                        <div style={{ flex: 1 }}>
                          <h4 style={{ fontSize: '0.95rem', color: '#ffffff', marginBottom: '0.25rem' }}>Document Quality Profile</h4>
                          <p style={{ fontSize: '0.85rem' }}>
                            Word Count: <strong>{sandboxQualityResult.metrics.word_count}</strong> | Noise Ratio: <strong>{(sandboxQualityResult.metrics.noise_ratio * 100).toFixed(1)}%</strong>
                          </p>
                        </div>
                      </div>

                      <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Sub-score Breakdowns</h4>
                      <div className="bar-chart-list">
                        
                        <div className="bar-chart-row">
                          <div className="bar-chart-label-group">
                            <span className="bar-chart-label">Document Length (15%)</span>
                            <span className="bar-chart-value">{(sandboxQualityResult.sub_scores.length_score * 100).toFixed(0)}/100</span>
                          </div>
                          <div className="bar-chart-track">
                            <div className="bar-chart-fill primary-color" style={{ width: `${sandboxQualityResult.sub_scores.length_score * 100}%` }}></div>
                          </div>
                        </div>

                        <div className="bar-chart-row">
                          <div className="bar-chart-label-group">
                            <span className="bar-chart-label">Language Confidence (20%)</span>
                            <span className="bar-chart-value">{(sandboxQualityResult.sub_scores.stop_word_score * 100).toFixed(0)}/100</span>
                          </div>
                          <div className="bar-chart-track">
                            <div className="bar-chart-fill primary-color" style={{ width: `${sandboxQualityResult.sub_scores.stop_word_score * 100}%` }}></div>
                          </div>
                        </div>

                        <div className="bar-chart-row">
                          <div className="bar-chart-label-group">
                            <span className="bar-chart-label">Readability Index (20%)</span>
                            <span className="bar-chart-value">{(sandboxQualityResult.sub_scores.readability_score * 100).toFixed(0)}/100</span>
                          </div>
                          <div className="bar-chart-track">
                            <div className="bar-chart-fill primary-color" style={{ width: `${sandboxQualityResult.sub_scores.readability_score * 100}%` }}></div>
                          </div>
                        </div>

                        <div className="bar-chart-row">
                          <div className="bar-chart-label-group">
                            <span className="bar-chart-label">Noise Ratio (15%)</span>
                            <span className="bar-chart-value">{(sandboxQualityResult.sub_scores.noise_score * 100).toFixed(0)}/100</span>
                          </div>
                          <div className="bar-chart-track">
                            <div className="bar-chart-fill primary-color" style={{ width: `${sandboxQualityResult.sub_scores.noise_score * 100}%` }}></div>
                          </div>
                        </div>

                        <div className="bar-chart-row">
                          <div className="bar-chart-label-group">
                            <span className="bar-chart-label">Repetitiveness (15%)</span>
                            <span className="bar-chart-value">{(sandboxQualityResult.sub_scores.repetition_score * 100).toFixed(0)}/100</span>
                          </div>
                          <div className="bar-chart-track">
                            <div className="bar-chart-fill primary-color" style={{ width: `${sandboxQualityResult.sub_scores.repetition_score * 100}%` }}></div>
                          </div>
                        </div>

                        <div className="bar-chart-row">
                          <div className="bar-chart-label-group">
                            <span className="bar-chart-label">Malformed Text (15%)</span>
                            <span className="bar-chart-value">{(sandboxQualityResult.sub_scores.malformed_score * 100).toFixed(0)}/100</span>
                          </div>
                          <div className="bar-chart-track">
                            <div className="bar-chart-fill primary-color" style={{ width: `${sandboxQualityResult.sub_scores.malformed_score * 100}%` }}></div>
                          </div>
                        </div>

                      </div>
                    </div>
                  )}
                </div>

                <div className="glass-card">
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '0.5rem', color: '#ffffff' }}>Run Database Scoring Job</h3>
                  <p style={{ fontSize: '0.9rem', marginBottom: '1.25rem' }}>Runs heuristics calculations over all unscored documents inside database, updating quality values.</p>
                  
                  <button onClick={handleBatchQuality} className="btn btn-secondary" disabled={batchQualityLoading}>
                    {batchQualityLoading ? 'Evaluating...' : 'Run Quality Evaluation'}
                  </button>

                  {batchQualityMessage && (
                    <div style={{ marginTop: '1rem', padding: '0.75rem 1rem', borderRadius: '0.5rem', background: 'rgba(255,255,255,0.03)', fontSize: '0.9rem', color: 'var(--success)', border: '1px solid var(--card-border)' }}>
                      {batchQualityMessage}
                    </div>
                  )}
                </div>
              </>
            )}

            {/* ==========================================
                TAB: DATASET ANALYTICS
                ========================================== */}
            {activeTab === 'analytics' && (
              <>
                <div style={{ borderBottom: '1px solid var(--card-border)', paddingBottom: '1rem' }}>
                  <h2 style={{ fontSize: '1.75rem', color: '#ffffff' }}>📈 Dataset Analytics</h2>
                  <p style={{ fontSize: '0.95rem', marginTop: '0.25rem' }}>Detailed heuristics, top keyword metrics, and distribution charts of database records.</p>
                </div>

                {analyticsLoading && !analytics ? (
                  <p style={{ color: 'var(--text-secondary)' }}>Loading analytics payload from API...</p>
                ) : analyticsError ? (
                  <p style={{ color: 'var(--error)' }}>Error: {analyticsError}</p>
                ) : analytics ? (
                  <>
                    {/* Basic Length Info */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem' }}>
                      <div className="glass-card" style={{ padding: '1.5rem' }}>
                        <h4 style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Avg Word Count</h4>
                        <span style={{ fontSize: '2rem', fontWeight: 800, color: '#ffffff', display: 'block', margin: '0.5rem 0' }}>
                          {analytics.length_stats.avg_word_count.toFixed(1)}
                        </span>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Median: {analytics.length_stats.median_word_count}</p>
                      </div>

                      <div className="glass-card" style={{ padding: '1.5rem' }}>
                        <h4 style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Avg Char Count</h4>
                        <span style={{ fontSize: '2rem', fontWeight: 800, color: '#ffffff', display: 'block', margin: '0.5rem 0' }}>
                          {analytics.length_stats.avg_char_count.toFixed(0)}
                        </span>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Median: {analytics.length_stats.median_char_count}</p>
                      </div>

                      <div className="glass-card" style={{ padding: '1.5rem' }}>
                        <h4 style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Min/Max Quality</h4>
                        <span style={{ fontSize: '2rem', fontWeight: 800, color: '#ffffff', display: 'block', margin: '0.5rem 0' }}>
                          {analytics.quality_stats.min_score.toFixed(0)} - {analytics.quality_stats.max_score.toFixed(0)}
                        </span>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Median Quality: {analytics.quality_stats.median_score}</p>
                      </div>
                    </div>

                    {/* SVG distributions grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
                      
                      {/* 1. Language Distribution */}
                      <div className="glass-card">
                        <h3 style={{ fontSize: '1.1rem', marginBottom: '1.25rem', color: '#ffffff' }}>Language Distribution</h3>
                        <div className="bar-chart-list">
                          {Object.entries(analytics.language_distribution).map(([lang, count]) => {
                            const pct = analytics.total_documents > 0 ? (count / analytics.total_documents) * 100 : 0;
                            return (
                              <div key={lang} className="bar-chart-row">
                                <div className="bar-chart-label-group">
                                  <span className="bar-chart-label">{lang.toUpperCase()}</span>
                                  <span className="bar-chart-value">{count} ({pct.toFixed(0)}%)</span>
                                </div>
                                <div className="bar-chart-track">
                                  <div className="bar-chart-fill primary-color" style={{ width: `${pct}%` }}></div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* 2. Source Distribution */}
                      <div className="glass-card">
                        <h3 style={{ fontSize: '1.1rem', marginBottom: '1.25rem', color: '#ffffff' }}>Source Distribution</h3>
                        <div className="bar-chart-list">
                          {Object.entries(analytics.source_distribution).map(([src, count]) => {
                            const pct = analytics.total_documents > 0 ? (count / analytics.total_documents) * 100 : 0;
                            return (
                              <div key={src} className="bar-chart-row">
                                <div className="bar-chart-label-group">
                                  <span className="bar-chart-label">{src}</span>
                                  <span className="bar-chart-value">{count} ({pct.toFixed(0)}%)</span>
                                </div>
                                <div className="bar-chart-track">
                                  <div className="bar-chart-fill primary-color" style={{ width: `${pct}%` }}></div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* 3. Quality Distribution (Buckets) */}
                      <div className="glass-card">
                        <h3 style={{ fontSize: '1.1rem', marginBottom: '1.25rem', color: '#ffffff' }}>Quality Grade Buckets</h3>
                        <div className="bar-chart-list">
                          {Object.entries(analytics.quality_stats.buckets).map(([bucket, count]) => {
                            // Sum quality score counts
                            const totalScores = Object.values(analytics.quality_stats.buckets).reduce((s, c) => s + c, 0);
                            const pct = totalScores > 0 ? (count / totalScores) * 100 : 0;
                            return (
                              <div key={bucket} className="bar-chart-row">
                                <div className="bar-chart-label-group">
                                  <span className="bar-chart-label">Score {bucket}</span>
                                  <span className="bar-chart-value">{count} ({pct.toFixed(0)}%)</span>
                                </div>
                                <div className="bar-chart-track">
                                  <div className="bar-chart-fill success-color" style={{ width: `${pct}%` }}></div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* 4. Top Keywords */}
                      <div className="glass-card">
                        <h3 style={{ fontSize: '1.1rem', marginBottom: '1.25rem', color: '#ffffff' }}>Top 10 Keywords</h3>
                        
                        <div className="data-table-container">
                          <table className="data-table">
                            <thead>
                              <tr>
                                <th>Keyword</th>
                                <th>Frequencies</th>
                              </tr>
                            </thead>
                            <tbody>
                              {analytics.top_keywords.map((kw, i) => (
                                <tr key={i}>
                                  <td style={{ fontWeight: 600, color: 'var(--primary)' }}>{kw.word}</td>
                                  <td className="mono-cell">{kw.frequency}</td>
                                </tr>
                              ))}
                              {analytics.top_keywords.length === 0 && (
                                <tr>
                                  <td colSpan={2} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No keywords extracted.</td>
                                </tr>
                              )}
                            </tbody>
                          </table>
                        </div>
                      </div>

                    </div>
                  </>
                ) : (
                  <p style={{ color: 'var(--text-muted)' }}>No database records populated.</p>
                )}
              </>
            )}

            {/* ==========================================
                TAB: DATASET EXPORT
                ========================================== */}
            {activeTab === 'export' && (
              <>
                <div style={{ borderBottom: '1px solid var(--card-border)', paddingBottom: '1rem' }}>
                  <h2 style={{ fontSize: '1.75rem', color: '#ffffff' }}>📦 Dataset Export</h2>
                  <p style={{ fontSize: '0.95rem', marginTop: '0.25rem' }}>Apply dynamic database query filters and download dataset packages.</p>
                </div>

                <div className="glass-card">
                  <div className="form-card">
                    
                    <div className="form-row">
                      <div className="field-group">
                        <label htmlFor="export-format">File Format</label>
                        <select id="export-format" className="input-select" value={exportFormat} onChange={(e) => setExportFormat(e.target.value)}>
                          <option value="csv">CSV Table (.csv)</option>
                          <option value="json">JSON Array (.json)</option>
                          <option value="parquet">Apache Parquet (.parquet)</option>
                        </select>
                      </div>

                      <div className="field-group">
                        <label htmlFor="export-source">Filter by Source</label>
                        <input id="export-source" type="text" className="input-text" placeholder="e.g. web_news" value={exportSource} onChange={(e) => setExportSource(e.target.value)} />
                      </div>
                    </div>

                    <div className="form-row">
                      <div className="field-group">
                        <label htmlFor="export-language">Filter by Language</label>
                        <input id="export-language" type="text" className="input-text" placeholder="e.g. en" value={exportLanguage} onChange={(e) => setExportLanguage(e.target.value)} />
                      </div>

                      <div className="field-group">
                        <label htmlFor="export-quality">Minimum Quality Score: {exportMinQuality}</label>
                        <input id="export-quality" type="range" min={0} max={100} step={5} className="input-text" style={{ padding: '0.25rem' }} value={exportMinQuality} onChange={(e) => setExportMinQuality(parseInt(e.target.value))} />
                      </div>
                    </div>

                    <div className="field-group" style={{ flexDirection: 'row', alignItems: 'center', gap: '0.75rem' }}>
                      <input id="export-dedup" type="checkbox" style={{ width: '1.25rem', height: '1.25rem', accentColor: 'var(--primary)' }} checked={exportExcludeDuplicates} onChange={(e) => setExportExcludeDuplicates(e.target.checked)} />
                      <label htmlFor="export-dedup" style={{ textTransform: 'none', fontSize: '0.95rem', cursor: 'pointer' }}>Exclude duplicates from export (hide duplicate_flag=True)</label>
                    </div>

                    <button onClick={handleDownloadExport} className="btn btn-primary" style={{ alignSelf: 'flex-start', marginTop: '1rem' }} disabled={exportLoading}>
                      {exportLoading ? 'Compiling Dataset File...' : 'Download Export Package'}
                    </button>
                  </div>

                  {exportMessage && (
                    <div style={{ marginTop: '1.25rem', padding: '0.75rem 1rem', borderRadius: '0.5rem', background: 'rgba(255,255,255,0.03)', fontSize: '0.9rem', color: exportMessage.startsWith('Error') ? 'var(--error)' : 'var(--success)', border: '1px solid var(--card-border)' }}>
                      {exportMessage}
                    </div>
                  )}
                </div>

                <div className="glass-card">
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#ffffff' }}>Export Integration Specifications</h3>
                  <p style={{ fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
                    Parquet exports are generated binary buffers leveraging PyArrow and can be instantly loaded into ML models or Pandas data frames:
                  </p>
                  <pre style={{ background: '#111827', padding: '1rem', borderRadius: '0.5rem', marginTop: '1rem', fontSize: '0.85rem', fontFamily: 'var(--font-mono)', border: '1px solid rgba(255,255,255,0.05)', overflowX: 'auto', color: 'var(--primary)' }}>
                    import pandas as pd{'\n'}
                    df = pd.read_parquet("dataset_export.parquet"){'\n'}
                    print(df.head())
                  </pre>
                </div>
              </>
            )}

            {/* ==========================================
                TAB: ONE-CLICK PIPELINE
                ========================================== */}
            {activeTab === 'pipeline' && (
              <>
                <div style={{ borderBottom: '1px solid var(--card-border)', paddingBottom: '1rem' }}>
                  <h2 style={{ fontSize: '1.75rem', color: '#ffffff' }}>🚀 One-Click Pipeline Orchestrator</h2>
                  <p style={{ fontSize: '0.95rem', marginTop: '0.25rem' }}>Execute Collect → Clean → Dedup → Score → Export sequentially.</p>
                </div>

                <div className="glass-card">
                  <form onSubmit={handleTriggerPipeline} className="form-card">
                    <div className="field-group">
                      <label htmlFor="pipeline-urls">Seed URLs (one per line)</label>
                      <textarea id="pipeline-urls" rows={4} className="input-textarea" value={pipelineUrls} onChange={(e) => setPipelineUrls(e.target.value)} required />
                    </div>

                    <div className="form-row">
                      <div className="field-group">
                        <label htmlFor="pipeline-format">Export Output Format</label>
                        <select id="pipeline-format" className="input-select" value={pipelineFormat} onChange={(e) => setPipelineFormat(e.target.value)}>
                          <option value="parquet">Apache Parquet (.parquet)</option>
                          <option value="csv">CSV Table (.csv)</option>
                          <option value="json">JSON Array (.json)</option>
                        </select>
                      </div>

                      <div className="field-group">
                        <label htmlFor="pipeline-threshold">Deduplication Hamming Limit: {pipelineThreshold}</label>
                        <input id="pipeline-threshold" type="range" min={3} max={25} className="input-text" style={{ padding: '0.25rem' }} value={pipelineThreshold} onChange={(e) => setPipelineThreshold(parseInt(e.target.value))} />
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '1rem' }}>
                      <button type="submit" className="btn btn-primary" disabled={pipelineRunning}>
                        {pipelineRunning ? 'Pipeline Running...' : 'Launch One-Click Pipeline'}
                      </button>
                      {pipelineRunning && pipelineJobId && (
                        <button type="button" onClick={handleCancelPipeline} className="btn btn-secondary" style={{ borderColor: 'var(--error)', color: 'var(--error)' }}>
                          Cancel Pipeline
                        </button>
                      )}
                      {pipelineStatus && pipelineStatus.status === 'completed' && (
                        <button type="button" onClick={handleDownloadPipelineExport} className="btn btn-secondary" style={{ borderColor: 'var(--success)', color: 'var(--success)' }}>
                          Download Exported Dataset
                        </button>
                      )}
                    </div>
                  </form>

                  {pipelineMessage && (
                    <div style={{ marginTop: '1.25rem', padding: '0.75rem 1rem', borderRadius: '0.5rem', background: 'rgba(255,255,255,0.03)', fontSize: '0.95rem', color: 'var(--primary)', border: '1px solid var(--card-border)' }}>
                      {pipelineMessage}
                    </div>
                  )}
                </div>

                {/* Pipeline Progress Monitor */}
                {pipelineStatus && (
                  <div className="glass-card">
                    <h3 style={{ fontSize: '1.1rem', marginBottom: '1.25rem', color: '#ffffff' }}>Pipeline Monitor</h3>
                    
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                      <span>Stage: <strong style={{ color: 'var(--primary)', textTransform: 'uppercase' }}>{pipelineStatus.stage}</strong></span>
                      <span style={{ fontFamily: 'var(--font-mono)' }}>{pipelineStatus.progress.toFixed(0)}%</span>
                    </div>

                    {/* Progress Bar Track */}
                    <div className="bar-chart-track" style={{ height: '14px', borderRadius: '7px', marginBottom: '1.5rem' }}>
                      <div className={`bar-chart-fill ${pipelineStatus.status === 'failed' ? 'unhealthy' : pipelineStatus.status === 'completed' ? 'success-color' : ''}`} style={{ width: `${pipelineStatus.progress}%`, height: '100%' }}></div>
                    </div>

                    <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '0.75rem' }}>Execution Logs</h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.9rem' }}>
                      
                      <div style={{ display: 'flex', justifyContent: 'space-between', opacity: pipelineStatus.progress >= 10 ? 1 : 0.4 }}>
                        <span>1. Collect raw text documents (Seed URLs)</span>
                        <span style={{ color: pipelineStatus.progress > 10 ? 'var(--success)' : pipelineStatus.progress === 10 ? 'var(--warning)' : 'var(--text-muted)' }}>
                          {pipelineStatus.progress > 10 ? '✓ Done' : pipelineStatus.progress === 10 ? '● Running...' : 'Waiting'}
                        </span>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', opacity: pipelineStatus.progress >= 35 ? 1 : 0.4 }}>
                        <span>2. Clean boilerplate ads, headers, footers & unicode</span>
                        <span style={{ color: pipelineStatus.progress > 35 ? 'var(--success)' : pipelineStatus.progress === 35 ? 'var(--warning)' : 'var(--text-muted)' }}>
                          {pipelineStatus.progress > 35 ? '✓ Done' : pipelineStatus.progress === 35 ? '● Running...' : 'Waiting'}
                        </span>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', opacity: pipelineStatus.progress >= 55 ? 1 : 0.4 }}>
                        <span>3. Deduplicate exact hashes & SimHash near-duplicates</span>
                        <span style={{ color: pipelineStatus.progress > 55 ? 'var(--success)' : pipelineStatus.progress === 55 ? 'var(--warning)' : 'var(--text-muted)' }}>
                          {pipelineStatus.progress > 55 ? '✓ Done' : pipelineStatus.progress === 55 ? '● Running...' : 'Waiting'}
                        </span>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', opacity: pipelineStatus.progress >= 75 ? 1 : 0.4 }}>
                        <span>4. Evaluate composite document quality scores</span>
                        <span style={{ color: pipelineStatus.progress > 75 ? 'var(--success)' : pipelineStatus.progress === 75 ? 'var(--warning)' : 'var(--text-muted)' }}>
                          {pipelineStatus.progress > 75 ? '✓ Done' : pipelineStatus.progress === 75 ? '● Running...' : 'Waiting'}
                        </span>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', opacity: pipelineStatus.progress >= 90 ? 1 : 0.4 }}>
                        <span>5. Package and export filtered final dataset</span>
                        <span style={{ color: pipelineStatus.progress > 90 ? 'var(--success)' : pipelineStatus.progress === 90 ? 'var(--warning)' : 'var(--text-muted)' }}>
                          {pipelineStatus.progress > 90 ? '✓ Done' : pipelineStatus.progress === 90 ? '● Running...' : 'Waiting'}
                        </span>
                      </div>

                    </div>
                  </div>
                )}

                <div className="glass-card">
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: '#ffffff' }}>Export Integration Specifications</h3>
                  <p style={{ fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
                    Parquet exports are generated binary buffers leveraging PyArrow and can be instantly loaded into ML models or Pandas data frames:
                  </p>
                  <pre style={{ background: '#111827', padding: '1rem', borderRadius: '0.5rem', marginTop: '1rem', fontSize: '0.85rem', fontFamily: 'var(--font-mono)', border: '1px solid rgba(255,255,255,0.05)', overflowX: 'auto', color: 'var(--primary)' }}>
                    import pandas as pd{'\n'}
                    df = pd.read_parquet("dataset_export.parquet"){'\n'}
                    print(df.head())
                  </pre>
                </div>
              </>
            )}

          </section>
        </div>
      </main>

      <footer className="footer">
        <div className="container footer-content">
          <div>
            &copy; 2026 <strong>DataForge AI</strong>. All rights reserved.
          </div>
          <div className="footer-links">
            <a href={`${apiUrl}/docs`} className="footer-link" target="_blank" rel="noopener noreferrer">FastAPI API Docs</a>
            <a href="https://github.com" className="footer-link" target="_blank" rel="noopener noreferrer">GitHub Project</a>
          </div>
        </div>
      </footer>
    </>
  );
}
