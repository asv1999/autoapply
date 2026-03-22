import { useState, useEffect, useCallback } from 'react';

const API = 'http://localhost:8000/api';

async function api(path, opts = {}) {
  const r = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!r.ok) throw new Error(`API error: ${r.status}`);
  return r.json();
}

export default function App() {
  const [tab, setTab] = useState('dashboard');
  const [dashboard, setDashboard] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [status, setStatus] = useState('');
  const [jobInput, setJobInput] = useState('');
  const [loading, setLoading] = useState({});

  // Load data
  const refresh = useCallback(async () => {
    try {
      const [d, j, a] = await Promise.all([
        api('/dashboard'),
        api('/jobs?limit=200'),
        api('/analytics'),
      ]);
      setDashboard(d);
      setJobs(j);
      setAnalytics(a);
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { refresh(); const i = setInterval(refresh, 15000); return () => clearInterval(i); }, [refresh]);

  // Actions
  const runDiscovery = async () => {
    setLoading(p => ({...p, discover: true}));
    try {
      const r = await api('/discover', { method: 'POST' });
      setStatus(`Discovery started: ${r.run_id}`);
    } catch(e) { setStatus(`Error: ${e.message}`); }
    setLoading(p => ({...p, discover: false}));
  };

  const addManualJobs = async () => {
    const lines = jobInput.split('\n').filter(l => l.trim());
    const parsed = lines.map(l => {
      const p = l.split('|').map(s => s.trim());
      return { title: p[0]||'', company: p[1]||'', location: p[2]||'', url: p[3]||'', requirements: (p[4]||'').split(',').map(s=>s.trim()), decision_maker: p[5]||'' };
    }).filter(j => j.title && j.company);
    
    if (!parsed.length) { setStatus('No valid jobs found. Use: Title | Company | Location | URL | Reqs | DM'); return; }
    const r = await api('/jobs/manual', { method: 'POST', body: JSON.stringify(parsed) });
    setStatus(`Added ${r.inserted} jobs (${r.duplicates} duplicates skipped)`);
    setJobInput('');
    refresh();
  };

  const runPlaybook = async () => {
    setLoading(p => ({...p, playbook: true}));
    setStatus('Generating playbook with Llama3...');
    try {
      const r = await api('/playbook', { method: 'POST' });
      setStatus(`Playbook ready: ${r.jobs_analyzed} jobs analyzed, ${r.tokens} tokens`);
    } catch(e) { setStatus(`Error: ${e.message}`); }
    setLoading(p => ({...p, playbook: false}));
  };

  const runTailor = async () => {
    setLoading(p => ({...p, tailor: true}));
    setStatus('Tailoring resumes...');
    try {
      const r = await api('/tailor', { method: 'POST' });
      setStatus(`Tailored ${r.tailored} resumes`);
    } catch(e) { setStatus(`Error: ${e.message}`); }
    setLoading(p => ({...p, tailor: false}));
  };

  const genDocs = async () => {
    setLoading(p => ({...p, docs: true}));
    try {
      const r = await api('/generate-docs/batch', { method: 'POST' });
      setStatus(`Generated ${r.generated} documents`);
    } catch(e) { setStatus(`Error: ${e.message}`); }
    setLoading(p => ({...p, docs: false}));
  };

  const stats = dashboard?.applications || {};
  const s = { fontFamily: "'Inter','DM Sans',system-ui,sans-serif", background: '#09090b', color: '#e4e4e7', minHeight: '100vh' };
  const card = { background: '#111116', border: '1px solid #1e1e24', borderRadius: 10, padding: 20 };
  const btn = (color, dis) => ({ padding: '10px 20px', fontSize: 13, fontWeight: 700, border: 'none', borderRadius: 8, background: dis ? '#1e1e24' : color, color: dis ? '#3f3f46' : '#fff', cursor: dis ? 'not-allowed' : 'pointer', opacity: dis ? 0.5 : 1 });

  return (
    <div style={s}>
      {/* Header */}
      <div style={{ background: '#111116', borderBottom: '1px solid #1e1e24', padding: '16px 28px', position: 'sticky', top: 0, zIndex: 100 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 800, margin: 0, color: '#fafafa' }}>AutoApply</h1>
            <p style={{ fontSize: 11, color: '#52525b', margin: '2px 0 0' }}>
              {dashboard?.total_jobs_discovered || 0} jobs discovered · {stats.submitted || 0} applied · {stats.interviews || 0} interviews
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {['dashboard', 'jobs', 'pipeline', 'analytics'].map(t => (
              <button key={t} onClick={() => setTab(t)} style={{ padding: '6px 14px', fontSize: 12, fontWeight: tab===t?700:400, border: 'none', borderBottom: tab===t?'2px solid #a78bfa':'2px solid transparent', background: 'transparent', color: tab===t?'#e4e4e7':'#52525b', cursor: 'pointer', textTransform: 'capitalize' }}>{t}</button>
            ))}
          </div>
        </div>
        {status && <div style={{ marginTop: 8, padding: '6px 12px', background: '#a78bfa10', border: '1px solid #a78bfa20', borderRadius: 6, fontSize: 12, color: '#a1a1aa' }}>{status}</div>}
      </div>

      <div style={{ padding: '20px 28px', maxWidth: 1200, margin: '0 auto' }}>

        {/* ═══ DASHBOARD ═══ */}
        {tab === 'dashboard' && (
          <div>
            {/* Stat Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 12, marginBottom: 20 }}>
              {[
                { label: 'Jobs Found', value: dashboard?.total_jobs_discovered || 0, color: '#eab308' },
                { label: 'Applied', value: stats.submitted || 0, color: '#38bdf8' },
                { label: 'Callbacks', value: stats.callbacks || 0, color: '#a78bfa' },
                { label: 'Interviews', value: stats.interviews || 0, color: '#22c55e' },
                { label: 'Offers', value: stats.offers || 0, color: '#f472b6' },
                { label: 'Callback Rate', value: `${stats.callback_rate || 0}%`, color: '#14b8a6' },
              ].map(s => (
                <div key={s.label} style={{ ...card, textAlign: 'center' }}>
                  <div style={{ fontSize: 28, fontWeight: 800, color: s.color }}>{s.value}</div>
                  <div style={{ fontSize: 11, color: '#52525b', marginTop: 4 }}>{s.label}</div>
                </div>
              ))}
            </div>

            {/* Pipeline Actions */}
            <div style={{ ...card, marginBottom: 20 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, margin: '0 0 12px', color: '#fafafa' }}>Run Pipeline</h3>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <button onClick={runDiscovery} disabled={loading.discover} style={btn('#eab308', loading.discover)}>
                  {loading.discover ? '⟳ Discovering...' : '1. Discover Jobs'}
                </button>
                <button onClick={runPlaybook} disabled={loading.playbook} style={btn('#a78bfa', loading.playbook)}>
                  {loading.playbook ? '⟳ Thinking...' : '2. Build Playbook'}
                </button>
                <button onClick={runTailor} disabled={loading.tailor} style={btn('#38bdf8', loading.tailor)}>
                  {loading.tailor ? '⟳ Tailoring...' : '3. Tailor Resumes'}
                </button>
                <button onClick={genDocs} disabled={loading.docs} style={btn('#22c55e', loading.docs)}>
                  {loading.docs ? '⟳ Generating...' : '4. Generate Docs'}
                </button>
              </div>
            </div>

            {/* Recent Runs */}
            <div style={card}>
              <h3 style={{ fontSize: 15, fontWeight: 700, margin: '0 0 12px', color: '#fafafa' }}>Recent Runs</h3>
              {(dashboard?.recent_runs || []).map((r, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #1a1a20', fontSize: 12 }}>
                  <span style={{ color: '#a1a1aa' }}>{new Date(r.started_at).toLocaleString()}</span>
                  <span>{r.jobs_discovered || 0} found · {r.jobs_new || 0} new</span>
                  <span style={{ color: r.status === 'completed' ? '#22c55e' : r.status === 'failed' ? '#ef4444' : '#eab308' }}>{r.status}</span>
                </div>
              ))}
              {(!dashboard?.recent_runs?.length) && <p style={{ color: '#3f3f46', fontSize: 12 }}>No runs yet. Click "Discover Jobs" to start.</p>}
            </div>
          </div>
        )}

        {/* ═══ JOBS TAB ═══ */}
        {tab === 'jobs' && (
          <div>
            {/* Manual Job Input */}
            <div style={{ ...card, marginBottom: 16 }}>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: '0 0 8px', color: '#eab308' }}>Add Jobs Manually</h3>
              <p style={{ fontSize: 11, color: '#52525b', margin: '0 0 8px' }}>Format: Title | Company | Location | URL | Requirements | Decision Maker</p>
              <textarea value={jobInput} onChange={e => setJobInput(e.target.value)} rows={5} placeholder="Strategy Analyst | TikTok | San Jose, CA | https://... | cross-functional, data science | VP Risk Strategy" style={{ width: '100%', padding: 10, fontSize: 12, fontFamily: 'monospace', background: '#09090b', border: '1px solid #1a1a20', borderRadius: 6, color: '#e4e4e7', resize: 'vertical' }} />
              <button onClick={addManualJobs} disabled={!jobInput.trim()} style={{ ...btn('#eab308', !jobInput.trim()), marginTop: 8 }}>Add Jobs</button>
            </div>

            {/* Job List */}
            <div style={card}>
              <h3 style={{ fontSize: 14, fontWeight: 700, margin: '0 0 12px', color: '#fafafa' }}>Job Queue ({jobs.length})</h3>
              <div style={{ maxHeight: 500, overflowY: 'auto' }}>
                {jobs.map((j, i) => (
                  <div key={j.id || i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #151518' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{j.title}</div>
                      <div style={{ fontSize: 11, color: '#52525b' }}>{j.company} · {j.location}</div>
                    </div>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {j.decision_maker && <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 3, background: '#eab30812', color: '#eab308' }}>{j.decision_maker}</span>}
                      {j.url && <a href={j.url} target="_blank" rel="noreferrer" style={{ fontSize: 10, padding: '2px 8px', borderRadius: 3, background: '#22c55e12', color: '#22c55e', textDecoration: 'none' }}>Apply</a>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ═══ PIPELINE ═══ */}
        {tab === 'pipeline' && (
          <div style={card}>
            <h3 style={{ fontSize: 15, fontWeight: 700, margin: '0 0 16px', color: '#fafafa' }}>Application Pipeline</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8 }}>
              {[
                { stage: 'Discovered', count: dashboard?.total_jobs_discovered || 0, color: '#eab308' },
                { stage: 'Tailored', count: stats.total || 0, color: '#a78bfa' },
                { stage: 'Applied', count: stats.submitted || 0, color: '#38bdf8' },
                { stage: 'Callbacks', count: stats.callbacks || 0, color: '#22c55e' },
                { stage: 'Interviews', count: stats.interviews || 0, color: '#f472b6' },
              ].map(s => (
                <div key={s.stage} style={{ textAlign: 'center', padding: 16, background: '#09090b', borderRadius: 8, border: '1px solid #1a1a20' }}>
                  <div style={{ fontSize: 24, fontWeight: 800, color: s.color }}>{s.count}</div>
                  <div style={{ fontSize: 11, color: '#52525b', marginTop: 4 }}>{s.stage}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ═══ ANALYTICS ═══ */}
        {tab === 'analytics' && analytics && (
          <div>
            <div style={{ ...card, marginBottom: 16 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, margin: '0 0 12px', color: '#fafafa' }}>Performance by Archetype</h3>
              {Object.entries(analytics.by_archetype || {}).map(([arch, data]) => (
                <div key={arch} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #151518', fontSize: 12 }}>
                  <span style={{ fontWeight: 600 }}>{arch}</span>
                  <span>{data.total} apps · {data.callback_rate}% callback · {data.interview_rate}% interview</span>
                </div>
              ))}
              {!Object.keys(analytics.by_archetype || {}).length && <p style={{ color: '#3f3f46', fontSize: 12 }}>No data yet. Update outcomes to see analytics.</p>}
            </div>

            <div style={card}>
              <h3 style={{ fontSize: 15, fontWeight: 700, margin: '0 0 12px', color: '#fafafa' }}>A/B Test Results</h3>
              <p style={{ fontSize: 12, color: '#a1a1aa', margin: '0 0 8px' }}>{analytics.ab_test?.recommendation || 'Not enough data yet.'}</p>
              {(analytics.ab_test?.variant_performance || []).map((v, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #151518', fontSize: 12 }}>
                  <span>Variant {v.variant}: {v.description}</span>
                  <span style={{ color: '#22c55e' }}>{v.success_rate}% success (n={v.total})</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
