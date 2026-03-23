import { useState, useEffect, useCallback } from 'react';

const API = '/api';
const api = async (path, opts = {}) => {
  const r = await fetch(`${API}${path}`, { headers: { 'Content-Type': 'application/json' }, ...opts });
  if (!r.ok) { const e = await r.text(); throw new Error(e); }
  return r.json();
};

// ─── STYLES ───
const s = {
  page: { fontFamily: "'Inter','DM Sans',system-ui,sans-serif", background: '#f8f9fa', color: '#1a1a2e', minHeight: '100vh' },
  nav: { background: '#fff', borderBottom: '1px solid #e9ecef', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 56, position: 'sticky', top: 0, zIndex: 100 },
  logo: { fontSize: 18, fontWeight: 700, color: '#1a1a2e', letterSpacing: '-0.3px' },
  tabs: { display: 'flex', gap: 0, height: '100%' },
  tab: (a) => ({ padding: '0 16px', fontSize: 13, fontWeight: a ? 600 : 400, color: a ? '#1a1a2e' : '#6c757d', background: 'none', border: 'none', borderBottom: a ? '2px solid #4361ee' : '2px solid transparent', cursor: 'pointer', height: '100%', display: 'flex', alignItems: 'center' }),
  card: { background: '#fff', borderRadius: 12, border: '1px solid #e9ecef', padding: '20px 24px', marginBottom: 16 },
  stat: { background: '#fff', borderRadius: 10, border: '1px solid #e9ecef', padding: '16px 20px', textAlign: 'center' },
  statN: { fontSize: 28, fontWeight: 700, color: '#1a1a2e' },
  statL: { fontSize: 12, color: '#6c757d', marginTop: 4 },
  btn: (c = '#4361ee', d = false) => ({ padding: '10px 20px', fontSize: 13, fontWeight: 600, border: 'none', borderRadius: 8, background: d ? '#e9ecef' : c, color: d ? '#adb5bd' : '#fff', cursor: d ? 'not-allowed' : 'pointer', opacity: d ? 0.7 : 1, transition: 'all 0.15s' }),
  btnO: (c = '#4361ee') => ({ padding: '8px 16px', fontSize: 12, fontWeight: 600, border: `1.5px solid ${c}`, borderRadius: 8, background: 'transparent', color: c, cursor: 'pointer' }),
  badge: (bg, fg) => ({ display: 'inline-block', fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 20, background: bg, color: fg }),
  input: { width: '100%', padding: '10px 14px', fontSize: 14, border: '1px solid #dee2e6', borderRadius: 8, outline: 'none', transition: 'border 0.15s' },
  label: { fontSize: 13, fontWeight: 600, color: '#495057', marginBottom: 6, display: 'block' },
  h2: { fontSize: 18, fontWeight: 700, color: '#1a1a2e', margin: '0 0 4px' },
  h3: { fontSize: 15, fontWeight: 600, color: '#1a1a2e', margin: '0 0 12px' },
  sub: { fontSize: 13, color: '#6c757d', margin: '0 0 16px' },
  row: { display: 'flex', gap: 12, flexWrap: 'wrap' },
  grid: (cols) => ({ display: 'grid', gridTemplateColumns: `repeat(auto-fill, minmax(${cols}px, 1fr))`, gap: 12 }),
};

// ─── SCORE BADGE ───
const ScoreBadge = ({ score }) => {
  if (!score) return null;
  const c = score >= 80 ? ['#d4edda','#155724'] : score >= 60 ? ['#fff3cd','#856404'] : ['#f8d7da','#721c24'];
  return <span style={s.badge(c[0], c[1])}>{Math.round(score)}% match</span>;
};

const StatusBadge = ({ status }) => {
  const m = { pending: ['#e9ecef','#495057'], submitted: ['#cce5ff','#004085'], ready_to_submit: ['#d4edda','#155724'], failed: ['#f8d7da','#721c24'], manual_review: ['#fff3cd','#856404'] };
  const c = m[status] || m.pending;
  return <span style={s.badge(c[0], c[1])}>{status}</span>;
};

const OutcomeBadge = ({ outcome }) => {
  const m = { unknown: ['#e9ecef','#495057'], callback: ['#cce5ff','#004085'], interview: ['#d4edda','#155724'], offer: ['#d4edda','#155724'], rejected: ['#f8d7da','#721c24'], ghosted: ['#e9ecef','#6c757d'] };
  const c = m[outcome] || m.unknown;
  return <span style={s.badge(c[0], c[1])}>{outcome}</span>;
};

// ═══ PAGE 1: ONBOARDING ═══
function Onboarding({ onComplete }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({ name:'', email:'', phone:'', location:'', linkedin_url:'', target_roles:'Strategy & Operations, Business Transformation, Management Consulting', salary_min:60000, salary_max:130000, education:'', skills:[], voice_rules:'Action verb + Context + Method + Quantified result. Mirror JD phrases. No em dashes.', proof_points:[], resume_bullets:{} });
  const [saving, setSaving] = useState(false);
  const [skillInput, setSkillInput] = useState('');
  const [ppInput, setPpInput] = useState('');

  const set = (k, v) => setForm(p => ({...p, [k]: v}));
  const addSkill = () => { if (skillInput.trim()) { set('skills', [...form.skills, skillInput.trim()]); setSkillInput(''); } };
  const addPP = () => { if (ppInput.trim()) { set('proof_points', [...form.proof_points, ppInput.trim()]); setPpInput(''); } };

  const save = async () => {
    setSaving(true);
    try { await api('/profile', { method: 'POST', body: JSON.stringify(form) }); onComplete(); }
    catch (e) { alert('Error: ' + e.message); }
    setSaving(false);
  };

  return (
    <div style={{ maxWidth: 640, margin: '40px auto', padding: '0 20px' }}>
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, color: '#1a1a2e', margin: '0 0 8px' }}>Welcome to AutoApply</h1>
        <p style={{ fontSize: 15, color: '#6c757d', margin: 0 }}>Let's set up your profile so AI can tailor your applications perfectly.</p>
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {[1,2,3].map(i => (
          <div key={i} style={{ flex: 1, height: 4, borderRadius: 2, background: step >= i ? '#4361ee' : '#e9ecef', transition: 'background 0.3s' }} />
        ))}
      </div>

      {step === 1 && (
        <div style={s.card}>
          <h2 style={s.h3}>Personal details</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div><label style={s.label}>Full name</label><input style={s.input} value={form.name} onChange={e=>set('name',e.target.value)} placeholder="Atharva Vaidya" /></div>
            <div><label style={s.label}>Email</label><input style={s.input} value={form.email} onChange={e=>set('email',e.target.value)} placeholder="you@email.com" /></div>
            <div><label style={s.label}>Phone</label><input style={s.input} value={form.phone} onChange={e=>set('phone',e.target.value)} /></div>
            <div><label style={s.label}>Location</label><input style={s.input} value={form.location} onChange={e=>set('location',e.target.value)} placeholder="Phoenix, AZ" /></div>
            <div style={{ gridColumn: '1/-1' }}><label style={s.label}>LinkedIn URL</label><input style={s.input} value={form.linkedin_url} onChange={e=>set('linkedin_url',e.target.value)} /></div>
            <div style={{ gridColumn: '1/-1' }}><label style={s.label}>Education</label><input style={s.input} value={form.education} onChange={e=>set('education',e.target.value)} placeholder="MBA, Thunderbird School of Global Management" /></div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
            <button style={s.btn('#4361ee', !form.name)} disabled={!form.name} onClick={()=>setStep(2)}>Continue</button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div style={s.card}>
          <h2 style={s.h3}>Target roles and skills</h2>
          <div><label style={s.label}>Target roles</label><input style={s.input} value={form.target_roles} onChange={e=>set('target_roles',e.target.value)} /></div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 12 }}>
            <div><label style={s.label}>Min salary ($)</label><input style={s.input} type="number" value={form.salary_min} onChange={e=>set('salary_min',parseInt(e.target.value)||0)} /></div>
            <div><label style={s.label}>Max salary ($)</label><input style={s.input} type="number" value={form.salary_max} onChange={e=>set('salary_max',parseInt(e.target.value)||0)} /></div>
          </div>
          <div style={{ marginTop: 12 }}>
            <label style={s.label}>Skills</label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input style={{...s.input, flex:1}} value={skillInput} onChange={e=>setSkillInput(e.target.value)} onKeyDown={e=>e.key==='Enter'&&addSkill()} placeholder="Add skill" />
              <button style={s.btnO('#4361ee')} onClick={addSkill}>Add</button>
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
              {form.skills.map((sk,i) => <span key={i} style={s.badge('#e8eafc','#4361ee')}>{sk} <span onClick={()=>set('skills',form.skills.filter((_,j)=>j!==i))} style={{cursor:'pointer',marginLeft:4}}>x</span></span>)}
            </div>
          </div>
          <div style={{ marginTop: 12 }}>
            <label style={s.label}>Key proof points (achievements)</label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input style={{...s.input, flex:1}} value={ppInput} onChange={e=>setPpInput(e.target.value)} onKeyDown={e=>e.key==='Enter'&&addPP()} placeholder="Vaxom $4M to $8.6M turnaround" />
              <button style={s.btnO('#4361ee')} onClick={addPP}>Add</button>
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
              {form.proof_points.map((pp,i) => <span key={i} style={s.badge('#d4edda','#155724')}>{pp} <span onClick={()=>set('proof_points',form.proof_points.filter((_,j)=>j!==i))} style={{cursor:'pointer',marginLeft:4}}>x</span></span>)}
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
            <button style={s.btnO('#6c757d')} onClick={()=>setStep(1)}>Back</button>
            <button style={s.btn()} onClick={()=>setStep(3)}>Continue</button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div style={s.card}>
          <h2 style={s.h3}>Voice and writing rules</h2>
          <p style={s.sub}>These rules ensure the AI writes like you, not like a generic template.</p>
          <textarea style={{...s.input, minHeight:100, resize:'vertical'}} value={form.voice_rules} onChange={e=>set('voice_rules',e.target.value)} />
          <div style={{ background: '#f8f9fa', borderRadius: 8, padding: 12, marginTop: 12, fontSize: 12, color: '#6c757d', lineHeight: 1.6 }}>
            <strong>Tip:</strong> Include your bullet formula (e.g., "Action + Context + Method + Result"), words to avoid, and tone preferences. The AI follows these exactly.
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
            <button style={s.btnO('#6c757d')} onClick={()=>setStep(2)}>Back</button>
            <button style={s.btn('#28a745', saving)} disabled={saving} onClick={save}>{saving ? 'Saving...' : 'Complete setup'}</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ═══ PAGE 2: DASHBOARD ═══
function Dashboard({ data, onAction, loading }) {
  const st = data?.applications || {};
  return (
    <div>
      <div style={s.grid(160)}>
        {[
          { n: data?.total_jobs || 0, l: 'Jobs found', c: '#4361ee' },
          { n: st.total || 0, l: 'Tailored', c: '#6f42c1' },
          { n: st.submitted || 0, l: 'Applied', c: '#20c997' },
          { n: st.callbacks || 0, l: 'Callbacks', c: '#fd7e14' },
          { n: st.interviews || 0, l: 'Interviews', c: '#28a745' },
          { n: `${st.callback_rate || 0}%`, l: 'Callback rate', c: '#17a2b8' },
        ].map((x, i) => (
          <div key={i} style={s.stat}>
            <div style={{ ...s.statN, color: x.c }}>{x.n}</div>
            <div style={s.statL}>{x.l}</div>
          </div>
        ))}
      </div>
      <div style={s.card}>
        <h3 style={s.h3}>Pipeline</h3>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <button style={s.btn('#4361ee', loading.discover)} disabled={loading.discover} onClick={() => onAction('discover')}>
            {loading.discover ? 'Discovering...' : '1. Discover jobs'}
          </button>
          <button style={s.btn('#6f42c1', loading.playbook)} disabled={loading.playbook} onClick={() => onAction('playbook')}>
            {loading.playbook ? 'Thinking...' : '2. Build playbook'}
          </button>
          <button style={s.btn('#20c997', loading.tailor)} disabled={loading.tailor} onClick={() => onAction('tailor')}>
            {loading.tailor ? 'Tailoring...' : '3. Tailor resumes'}
          </button>
          <button style={s.btn('#fd7e14', loading.docs)} disabled={loading.docs} onClick={() => onAction('docs')}>
            {loading.docs ? 'Generating...' : '4. Generate docs'}
          </button>
        </div>
      </div>
      {data?.recent_runs?.length > 0 && (
        <div style={s.card}>
          <h3 style={s.h3}>Recent runs</h3>
          {data.recent_runs.map((r, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f1f3f5', fontSize: 13 }}>
              <span style={{ color: '#6c757d' }}>{new Date(r.started_at).toLocaleString()}</span>
              <span>{r.jobs_discovered || 0} found, {r.jobs_new || 0} new</span>
              <span style={{ color: r.status === 'completed' ? '#28a745' : r.status === 'failed' ? '#dc3545' : '#fd7e14' }}>{r.status}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ═══ PAGE 3: JOBS ═══
function Jobs({ jobs, onRefresh }) {
  const [input, setInput] = useState('');
  const [adding, setAdding] = useState(false);
  const [selected, setSelected] = useState(null);
  const [connLoading, setConnLoading] = useState(false);
  const [connResult, setConnResult] = useState(null);

  const addManual = async () => {
    const lines = input.split('\n').filter(l => l.trim());
    const parsed = lines.map(l => { const p = l.split('|').map(x=>x.trim()); return {title:p[0]||'',company:p[1]||'',location:p[2]||'',url:p[3]||'',requirements:(p[4]||'').split(',').map(x=>x.trim()).filter(Boolean),decision_maker:p[5]||''}; }).filter(j=>j.title&&j.company);
    if (!parsed.length) return;
    setAdding(true);
    try {
      const r = await api('/jobs/manual', { method: 'POST', body: JSON.stringify(parsed) });
      setInput(''); onRefresh();
      alert(`Added ${r.inserted} jobs (${r.duplicates} duplicates skipped)`);
    } catch (e) { alert(e.message); }
    setAdding(false);
  };

  const findConnection = async (jid) => {
    setConnLoading(true); setConnResult(null);
    try { const r = await api(`/connections/${jid}`, { method: 'POST' }); setConnResult(r); }
    catch (e) { alert(e.message); }
    setConnLoading(false);
  };

  return (
    <div>
      <div style={s.card}>
        <h3 style={s.h3}>Add jobs manually</h3>
        <p style={{ fontSize: 12, color: '#6c757d', margin: '0 0 8px' }}>Format: Title | Company | Location | URL | Requirements | Decision Maker</p>
        <textarea style={{...s.input, minHeight:80, fontFamily:'monospace', fontSize:12}} value={input} onChange={e=>setInput(e.target.value)}
          placeholder={"Strategy Analyst | Google | NYC | https://... | analytics, strategy | VP Strategy"} />
        <button style={{...s.btn('#4361ee', adding||!input.trim()), marginTop:8}} disabled={adding||!input.trim()} onClick={addManual}>
          {adding ? 'Adding...' : 'Add jobs'}
        </button>
      </div>

      <div style={s.card}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h3 style={{...s.h3, margin:0}}>Job queue ({jobs.length})</h3>
          <button style={s.btnO('#4361ee')} onClick={onRefresh}>Refresh</button>
        </div>
        <div style={{ maxHeight: 500, overflowY: 'auto' }}>
          {jobs.map((j) => (
            <div key={j.id} style={{ padding: '12px 0', borderBottom: '1px solid #f1f3f5', cursor: 'pointer' }} onClick={() => setSelected(selected === j.id ? null : j.id)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{j.title}</div>
                  <div style={{ fontSize: 12, color: '#6c757d' }}>{j.company} · {j.location}</div>
                </div>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <ScoreBadge score={j.match_score} />
                  {j.archetype && <span style={s.badge('#e8eafc','#4361ee')}>{j.archetype}</span>}
                  {j.url && <a href={j.url} target="_blank" rel="noreferrer" onClick={e=>e.stopPropagation()} style={{...s.btnO('#28a745'), fontSize:11, padding:'4px 10px'}}>Apply</a>}
                </div>
              </div>
              {selected === j.id && (
                <div style={{ marginTop: 12, padding: 12, background: '#f8f9fa', borderRadius: 8, fontSize: 13 }}>
                  {j.requirements && <div style={{ marginBottom: 8 }}><strong>Requirements:</strong> {Array.isArray(j.requirements) ? j.requirements.join(', ') : j.requirements}</div>}
                  {j.decision_maker && <div style={{ marginBottom: 8 }}><strong>Decision maker:</strong> {j.decision_maker}</div>}
                  <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    <button style={s.btnO('#6f42c1')} onClick={(e)=>{e.stopPropagation();findConnection(j.id)}}>
                      {connLoading ? 'Finding...' : 'Find decision maker'}
                    </button>
                  </div>
                  {connResult && selected === j.id && (
                    <div style={{ marginTop: 12, padding: 12, background: '#fff', borderRadius: 8, border: '1px solid #e9ecef' }}>
                      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{connResult.contact_title}</div>
                      <div style={{ fontSize: 12, color: '#495057', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{connResult.outreach_message}</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
          {!jobs.length && <p style={{ color: '#adb5bd', fontSize: 13, textAlign: 'center', padding: 20 }}>No jobs yet. Run discovery or add manually.</p>}
        </div>
      </div>
    </div>
  );
}

// ═══ PAGE 4: RESUME STUDIO ═══
function ResumeStudio({ applications }) {
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [generating, setGenerating] = useState(false);

  const loadDetail = async (aid) => {
    setSelected(aid);
    try { const d = await api(`/applications/${aid}`); setDetail(d); }
    catch { setDetail(null); }
  };

  const genDoc = async (aid) => {
    setGenerating(true);
    try { await api(`/generate-docs/${aid}`, { method: 'POST' }); alert('Document generated'); }
    catch (e) { alert(e.message); }
    setGenerating(false);
  };

  return (
    <div>
      <div style={s.card}>
        <h3 style={s.h3}>Tailored applications ({applications.length})</h3>
        <div style={{ maxHeight: 500, overflowY: 'auto' }}>
          {applications.map(a => (
            <div key={a.id} style={{ padding: '12px 0', borderBottom: '1px solid #f1f3f5' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }} onClick={() => loadDetail(selected === a.id ? null : a.id)}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{a.title} <span style={{ fontWeight: 400, color: '#6c757d' }}>at {a.company}</span></div>
                  <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                    {a.archetype && <span style={s.badge('#e8eafc','#4361ee')}>{a.archetype}</span>}
                    <StatusBadge status={a.apply_status} />
                    <OutcomeBadge outcome={a.outcome} />
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button style={s.btnO('#4361ee')} onClick={e=>{e.stopPropagation();genDoc(a.id)}}>{generating?'...':'Generate .docx'}</button>
                </div>
              </div>
              {selected === a.id && detail && (
                <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div style={{ background: '#f8f9fa', borderRadius: 8, padding: 16 }}>
                    <h4 style={{ fontSize: 13, fontWeight: 700, color: '#4361ee', margin: '0 0 8px' }}>Tailored bullets</h4>
                    {detail.tailored_bullets && typeof detail.tailored_bullets === 'object' && Object.entries(detail.tailored_bullets).map(([sec, bullets]) => (
                      <div key={sec} style={{ marginBottom: 10 }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: '#6c757d', textTransform: 'uppercase', marginBottom: 3 }}>{sec.replace(/_/g,' ')}</div>
                        {Array.isArray(bullets) && bullets.map((b,i) => <p key={i} style={{ fontSize: 12, lineHeight: 1.5, margin: '3px 0', paddingLeft: 10, borderLeft: '2px solid #4361ee30' }}>{b}</p>)}
                      </div>
                    ))}
                  </div>
                  <div style={{ background: '#f8f9fa', borderRadius: 8, padding: 16 }}>
                    <h4 style={{ fontSize: 13, fontWeight: 700, color: '#6f42c1', margin: '0 0 8px' }}>Cover letter</h4>
                    <p style={{ fontSize: 12, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>{detail.cover_letter || 'Not generated yet'}</p>
                    {detail.outreach_message && (
                      <>
                        <h4 style={{ fontSize: 13, fontWeight: 700, color: '#fd7e14', margin: '16px 0 8px' }}>Outreach message</h4>
                        <p style={{ fontSize: 12, lineHeight: 1.6 }}>{detail.outreach_message}</p>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
          {!applications.length && <p style={{ color: '#adb5bd', fontSize: 13, textAlign: 'center', padding: 20 }}>No tailored applications yet. Run the pipeline first.</p>}
        </div>
      </div>
    </div>
  );
}

// ═══ PAGE 5: AUTO-APPLY ═══
function AutoApply({ applications }) {
  const pending = applications.filter(a => a.apply_status === 'pending' && a.tailored_bullets);
  const submitted = applications.filter(a => a.apply_status === 'submitted' || a.apply_status === 'ready_to_submit');

  const applyOne = async (aid) => {
    try { await api(`/apply/${aid}`, { method: 'POST' }); alert('Application started'); }
    catch (e) { alert(e.message); }
  };

  return (
    <div>
      <div style={s.card}>
        <div style={{ background: '#fff3cd', borderRadius: 8, padding: 12, marginBottom: 16, fontSize: 13, color: '#856404' }}>
          Auto-apply runs from your local machine using the CLI script. The web dashboard shows status and lets you trigger individual applications.
        </div>
        <h3 style={s.h3}>Pending ({pending.length})</h3>
        {pending.map(a => (
          <div key={a.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid #f1f3f5' }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{a.title} at {a.company}</div>
              <div style={{ fontSize: 11, color: '#6c757d' }}>{a.location}</div>
            </div>
            <button style={s.btnO('#28a745')} onClick={()=>applyOne(a.id)}>Apply</button>
          </div>
        ))}
        {!pending.length && <p style={{ color: '#adb5bd', fontSize: 13 }}>All caught up.</p>}
      </div>
      <div style={s.card}>
        <h3 style={s.h3}>Submitted ({submitted.length})</h3>
        {submitted.map(a => (
          <div key={a.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid #f1f3f5' }}>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600 }}>{a.title} at {a.company}</div>
            </div>
            <StatusBadge status={a.apply_status} />
          </div>
        ))}
      </div>
    </div>
  );
}

// ═══ PAGE 6: ANALYTICS ═══
function Analytics({ data, applications }) {
  const [updating, setUpdating] = useState(null);

  const updateOutcome = async (aid, outcome) => {
    setUpdating(aid);
    try { await api('/outcome', { method: 'POST', body: JSON.stringify({ application_id: aid, outcome }) }); }
    catch (e) { alert(e.message); }
    setUpdating(null);
  };

  const outcomes = ['callback','interview','offer','rejected','ghosted'];

  return (
    <div>
      {data?.archetypes && Object.keys(data.archetypes).length > 0 && (
        <div style={s.card}>
          <h3 style={s.h3}>Performance by archetype</h3>
          {Object.entries(data.archetypes).map(([arch, d]) => (
            <div key={arch} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f1f3f5', fontSize: 13 }}>
              <span style={{ fontWeight: 600 }}>{arch}</span>
              <span>{d.total} apps · {d.callback_rate}% callback · {d.interview_rate}% interview</span>
            </div>
          ))}
        </div>
      )}
      {data?.variants?.length > 0 && (
        <div style={s.card}>
          <h3 style={s.h3}>A/B test results</h3>
          {data.variants.map((v,i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f1f3f5', fontSize: 13 }}>
              <span>Variant {v.variant}: {v.description}</span>
              <span style={{ color: '#28a745', fontWeight: 600 }}>{v.success_rate}% (n={v.total})</span>
            </div>
          ))}
        </div>
      )}
      <div style={s.card}>
        <h3 style={s.h3}>Update outcomes</h3>
        <p style={s.sub}>Track which applications got responses to improve future tailoring.</p>
        {applications.filter(a=>a.apply_status==='submitted'||a.outcome==='unknown').slice(0,20).map(a => (
          <div key={a.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f1f3f5' }}>
            <div style={{ fontSize: 13 }}>{a.title} at {a.company}</div>
            <div style={{ display: 'flex', gap: 4 }}>
              {outcomes.map(o => (
                <button key={o} onClick={()=>updateOutcome(a.id,o)} disabled={updating===a.id}
                  style={{ padding: '4px 8px', fontSize: 10, fontWeight: 600, border: `1px solid ${o==='callback'?'#4361ee':o==='interview'?'#28a745':o==='offer'?'#28a745':'#dc3545'}20`,
                    borderRadius: 6, background: a.outcome===o?'#e8eafc':'transparent',
                    color: o==='callback'?'#4361ee':o==='interview'?'#28a745':o==='offer'?'#28a745':'#dc3545', cursor: 'pointer' }}>
                  {o}
                </button>
              ))}
            </div>
          </div>
        ))}
        {!applications.length && <p style={{ color: '#adb5bd', fontSize: 13 }}>No applications to track yet.</p>}
      </div>
    </div>
  );
}

// ═══ MAIN APP ═══
export default function App() {
  const [page, setPage] = useState('dashboard');
  const [data, setData] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [apps, setApps] = useState([]);
  const [analyticsData, setAnalytics] = useState(null);
  const [loading, setLoading] = useState({});
  const [status, setStatus] = useState('');
  const [needsOnboarding, setNeedsOnboarding] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [d, j, a, an] = await Promise.all([
        api('/dashboard'), api('/jobs?limit=200'), api('/applications?limit=200'), api('/analytics')
      ]);
      setData(d); setJobs(j); setApps(a); setAnalytics(an);
      setNeedsOnboarding(!d.profile_exists);
    } catch (e) { console.error(e); setNeedsOnboarding(true); }
  }, []);

  useEffect(() => { refresh(); const i = setInterval(refresh, 15000); return () => clearInterval(i); }, [refresh]);

  const action = async (type) => {
    setLoading(p => ({...p, [type]: true})); setStatus('');
    try {
      if (type === 'discover') { const r = await api('/discover', {method:'POST'}); setStatus(`Discovery started: ${r.run_id}`); }
      else if (type === 'playbook') { const r = await api('/playbook', {method:'POST'}); setStatus(`Playbook ready: ${r.jobs} jobs analyzed`); }
      else if (type === 'tailor') { const r = await api('/tailor', {method:'POST'}); setStatus(`Tailored ${r.tailored} resumes`); }
      else if (type === 'docs') { const r = await api('/generate-docs/batch', {method:'POST'}); setStatus(`Generated ${r.generated} documents`); }
      setTimeout(refresh, 2000);
    } catch (e) { setStatus(`Error: ${e.message}`); }
    setLoading(p => ({...p, [type]: false}));
  };

  if (needsOnboarding === null) return <div style={{...s.page, display:'flex',alignItems:'center',justifyContent:'center'}}><p>Loading...</p></div>;
  if (needsOnboarding) return <div style={s.page}><Onboarding onComplete={() => { setNeedsOnboarding(false); refresh(); }} /></div>;

  const pages = ['dashboard','jobs','resumes','apply','analytics'];

  return (
    <div style={s.page}>
      <div style={s.nav}>
        <span style={s.logo}>AutoApply</span>
        <div style={s.tabs}>
          {pages.map(p => (
            <button key={p} style={s.tab(page===p)} onClick={()=>setPage(p)}>
              {p.charAt(0).toUpperCase()+p.slice(1)}
            </button>
          ))}
        </div>
        <div style={{ fontSize: 12, color: '#6c757d' }}>{data?.total_jobs || 0} jobs · {(data?.applications?.total) || 0} apps</div>
      </div>

      {status && (
        <div style={{ margin: '16px 24px 0', padding: '10px 16px', background: status.includes('Error') ? '#f8d7da' : '#d4edda', borderRadius: 8, fontSize: 13, color: status.includes('Error') ? '#721c24' : '#155724' }}>
          {status}
        </div>
      )}

      <div style={{ padding: '20px 24px', maxWidth: 1000, margin: '0 auto' }}>
        {page === 'dashboard' && <Dashboard data={data} onAction={action} loading={loading} />}
        {page === 'jobs' && <Jobs jobs={jobs} onRefresh={refresh} />}
        {page === 'resumes' && <ResumeStudio applications={apps} />}
        {page === 'apply' && <AutoApply applications={apps} />}
        {page === 'analytics' && <Analytics data={analyticsData} applications={apps} />}
      </div>
    </div>
  );
}
