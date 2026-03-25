import { useState, useEffect, useCallback } from 'react';

const API = '/api';
const api = async (path, opts = {}) => {
  const r = await fetch(`${API}${path}`, { headers: { 'Content-Type': 'application/json' }, ...opts });
  if (!r.ok) { const e = await r.text(); throw new Error(e); }
  return r.json();
};
const uploadFile = async (path, file) => {
  const body = new FormData();
  body.append('file', file);
  const r = await fetch(`${API}${path}`, { method: 'POST', body });
  if (!r.ok) { const e = await r.text(); throw new Error(e); }
  return r.json();
};
const fileName = (path) => path ? path.split('/').pop() : '';
const fileUrl = (path) => `${API}${path}`;
const SECTION_NAMES = {digitech:'Digitech Services',asu:'Arizona State University',vaxom:'Vaxom Packaging',nccl:'National Commodities Clearing',vertiv:'Vertiv (Capstone)',km_capital:'KM Capital Partners',scdi:'Supply Chain DI Platform',gcn:'Global Careers Network'};
const DEFAULT_RESUME_BULLETS = {
  digitech: [
    'Led a business turnaround from $4M to $8.6M revenue in 10 months using Six Sigma DMAIC, improving operating discipline and accelerating commercial performance.',
    'Delivered 51% operational efficiency gains by designing AI transformation roadmaps for enterprise clients and aligning stakeholders around measurable adoption milestones.',
  ],
  asu: [
    'Completed 15+ consulting engagements across 5 continents at Thunderbird, building recommendations for growth strategy, market entry, and operating model design.',
    'Built a full-stack Supply Chain Decision Intelligence platform inspired by Microsoft OptiGuide to support scenario planning and data-backed decision making.',
    'Scored in the top 1% globally on the Bain Associate Consultant assessment, demonstrating structured problem solving and hypothesis-driven analysis.',
  ],
  vaxom: [
    'Built a commodity price forecasting model with 98% accuracy using 15 years of trade data to improve procurement and planning decisions.',
    'Uncovered a $1B+ inventory imbalance in a Fortune 500 global supply chain and presented findings to senior leadership to support corrective action.',
  ],
  nccl: [
    'Saved $100K annually and cut project intake time by 50% through workflow automation across 14 departments, improving delivery speed and operating consistency.',
    'Designed CRM and process automation that reduced manual coordination and improved cross-functional visibility for complex business operations.',
  ],
  vertiv: [
    'Presented high-stakes operational findings to C-suite stakeholders and translated analysis into practical recommendations for supply chain and inventory performance.',
  ],
  km_capital: [
    'Reduced marketing spend by 40%, saving $60K, by deploying generative AI outreach automation that improved targeting efficiency and campaign productivity.',
  ],
  scdi: [
    'Developed AI transformation and analytics solutions that connected operational data, forecasting, and scenario planning to executive decision making.',
    'Combined Python, SQL, Tableau, and business analysis to turn ambiguous operational problems into structured, measurable improvement programs.',
  ],
  gcn: [
    'Secured $24K in sponsorships and engaged 14,000+ students as President of the Global Careers Network, leading partnerships, events, and stakeholder outreach.',
    'Led cross-functional teams across global settings, balancing strategy, execution, and communication to deliver complex initiatives on tight timelines.',
  ],
};

const normalizeResumeBullets = (value) => {
  if (!value || typeof value !== 'object' || !Object.values(value).some(v => Array.isArray(v) && v.length)) return DEFAULT_RESUME_BULLETS;
  return { ...DEFAULT_RESUME_BULLETS, ...value };
};

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
  input: { width: '100%', padding: '10px 14px', fontSize: 14, border: '1px solid #dee2e6', borderRadius: 8, outline: 'none' },
  label: { fontSize: 13, fontWeight: 600, color: '#495057', marginBottom: 6, display: 'block' },
  h3: { fontSize: 15, fontWeight: 600, color: '#1a1a2e', margin: '0 0 12px' },
  sub: { fontSize: 13, color: '#6c757d', margin: '0 0 16px' },
  grid: (cols) => ({ display: 'grid', gridTemplateColumns: `repeat(auto-fill, minmax(${cols}px, 1fr))`, gap: 12 }),
};

const ScoreBadge = ({ score }) => {
  if (!score) return null;
  const c = score >= 80 ? ['#d4edda','#155724'] : score >= 60 ? ['#fff3cd','#856404'] : ['#f8d7da','#721c24'];
  return <span style={s.badge(c[0], c[1])}>{Math.round(score)}%</span>;
};
const StatusBadge = ({ status }) => {
  const m = { pending:['#e9ecef','#495057'], submitted:['#cce5ff','#004085'], ready_to_submit:['#d4edda','#155724'], failed:['#f8d7da','#721c24'] };
  return <span style={s.badge(...(m[status]||m.pending))}>{status}</span>;
};
const OutcomeBadge = ({ outcome }) => {
  const m = { unknown:['#e9ecef','#495057'], callback:['#cce5ff','#004085'], interview:['#d4edda','#155724'], offer:['#d1ecf1','#0c5460'], rejected:['#f8d7da','#721c24'], ghosted:['#e9ecef','#6c757d'] };
  return <span style={s.badge(...(m[outcome]||m.unknown))}>{outcome}</span>;
};

// ═══ ONBOARDING ═══
function Onboarding({ onComplete }) {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({ name:'', email:'', phone:'', location:'', linkedin_url:'', target_roles:'Strategy & Operations, Business Transformation, Management Consulting', salary_min:60000, salary_max:130000, education:'MGM Thunderbird School of Global Management (ASU) 2025, B.Tech VIT Pune 2021', skills:[], voice_rules:'Action verb + Context + Method + Quantified result. Mirror JD phrases. No em dashes, no delve/tapestry/passionate/cutting-edge.', proof_points:[], resume_bullets:{} });
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
        <p style={{ fontSize: 15, color: '#6c757d', margin: 0 }}>Set up your profile so AI can tailor applications perfectly.</p>
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        {[1,2,3].map(i => <div key={i} style={{ flex: 1, height: 4, borderRadius: 2, background: step >= i ? '#4361ee' : '#e9ecef' }} />)}
      </div>
      {step === 1 && <div style={s.card}>
        <h2 style={s.h3}>Personal details</h2>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div><label style={s.label}>Full name</label><input style={s.input} value={form.name} onChange={e=>set('name',e.target.value)} /></div>
          <div><label style={s.label}>Email</label><input style={s.input} value={form.email} onChange={e=>set('email',e.target.value)} /></div>
          <div><label style={s.label}>Phone</label><input style={s.input} value={form.phone} onChange={e=>set('phone',e.target.value)} /></div>
          <div><label style={s.label}>Location</label><input style={s.input} value={form.location} onChange={e=>set('location',e.target.value)} /></div>
          <div style={{gridColumn:'1/-1'}}><label style={s.label}>LinkedIn URL</label><input style={s.input} value={form.linkedin_url} onChange={e=>set('linkedin_url',e.target.value)} /></div>
          <div style={{gridColumn:'1/-1'}}><label style={s.label}>Education</label><input style={s.input} value={form.education} onChange={e=>set('education',e.target.value)} /></div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
          <button style={s.btn('#4361ee', !form.name)} disabled={!form.name} onClick={()=>setStep(2)}>Continue</button>
        </div>
      </div>}
      {step === 2 && <div style={s.card}>
        <h2 style={s.h3}>Target roles and skills</h2>
        <div><label style={s.label}>Target roles</label><input style={s.input} value={form.target_roles} onChange={e=>set('target_roles',e.target.value)} /></div>
        <div style={{ marginTop: 12 }}>
          <label style={s.label}>Skills</label>
          <div style={{ display: 'flex', gap: 8 }}><input style={{...s.input,flex:1}} value={skillInput} onChange={e=>setSkillInput(e.target.value)} onKeyDown={e=>e.key==='Enter'&&addSkill()} placeholder="Add skill" /><button style={s.btnO()} onClick={addSkill}>Add</button></div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>{form.skills.map((sk,i) => <span key={i} style={s.badge('#e8eafc','#4361ee')}>{sk} <span onClick={()=>set('skills',form.skills.filter((_,j)=>j!==i))} style={{cursor:'pointer'}}>x</span></span>)}</div>
        </div>
        <div style={{ marginTop: 12 }}>
          <label style={s.label}>Proof points</label>
          <div style={{ display: 'flex', gap: 8 }}><input style={{...s.input,flex:1}} value={ppInput} onChange={e=>setPpInput(e.target.value)} onKeyDown={e=>e.key==='Enter'&&addPP()} placeholder="Led turnaround from $4M to $8.6M" /><button style={s.btnO()} onClick={addPP}>Add</button></div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>{form.proof_points.map((pp,i) => <span key={i} style={s.badge('#d4edda','#155724')}>{pp} <span onClick={()=>set('proof_points',form.proof_points.filter((_,j)=>j!==i))} style={{cursor:'pointer'}}>x</span></span>)}</div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
          <button style={s.btnO('#6c757d')} onClick={()=>setStep(1)}>Back</button>
          <button style={s.btn()} onClick={()=>setStep(3)}>Continue</button>
        </div>
      </div>}
      {step === 3 && <div style={s.card}>
        <h2 style={s.h3}>Voice rules</h2>
        <p style={s.sub}>These rules ensure AI writes like you.</p>
        <textarea style={{...s.input, minHeight:100, resize:'vertical'}} value={form.voice_rules} onChange={e=>set('voice_rules',e.target.value)} />
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
          <button style={s.btnO('#6c757d')} onClick={()=>setStep(2)}>Back</button>
          <button style={s.btn('#28a745', saving)} disabled={saving} onClick={save}>{saving ? 'Saving...' : 'Complete setup'}</button>
        </div>
      </div>}
    </div>
  );
}

function ProfileAssets({ profile, onRefresh }) {
  const [uploading, setUploading] = useState('');

  const handleUpload = async (kind, file) => {
    if (!file) return;
    setUploading(kind);
    try {
      await uploadFile(kind === 'resume' ? '/profile/upload-resume' : '/profile/upload-cover-letter', file);
      await onRefresh();
    } catch (e) {
      alert(e.message);
    }
    setUploading('');
  };

  return <div style={s.card}>
    <h3 style={s.h3}>Base documents</h3>
    <p style={s.sub}>Upload the base resume and base cover letter you want AutoApply to keep on your profile.</p>
    <div style={s.grid(280)}>
      <div style={{background:'#f8f9fa',borderRadius:10,padding:16,border:'1px solid #e9ecef'}}>
        <div style={{fontSize:13,fontWeight:700,marginBottom:8}}>Base resume</div>
        <div style={{fontSize:12,color:'#6c757d',marginBottom:10}}>
          {profile?.resume_template_path ? fileName(profile.resume_template_path) : 'No base resume uploaded yet'}
        </div>
        <input
          type="file"
          accept=".doc,.docx,.pdf,.txt"
          onChange={e=>handleUpload('resume', e.target.files?.[0])}
          disabled={uploading === 'resume'}
          style={{fontSize:12}}
        />
      </div>
      <div style={{background:'#f8f9fa',borderRadius:10,padding:16,border:'1px solid #e9ecef'}}>
        <div style={{fontSize:13,fontWeight:700,marginBottom:8}}>Base cover letter</div>
        <div style={{fontSize:12,color:'#6c757d',marginBottom:10}}>
          {profile?.cover_letter_template_path ? fileName(profile.cover_letter_template_path) : 'No base cover letter uploaded yet'}
        </div>
        <input
          type="file"
          accept=".doc,.docx,.pdf,.txt"
          onChange={e=>handleUpload('cover', e.target.files?.[0])}
          disabled={uploading === 'cover'}
          style={{fontSize:12}}
        />
      </div>
    </div>
  </div>;
}

function BaseResumeEditor({ profile, onRefresh }) {
  const [sections, setSections] = useState(normalizeResumeBullets(profile?.resume_bullets));
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setSections(normalizeResumeBullets(profile?.resume_bullets));
  }, [profile]);

  const updateSection = (key, raw) => {
    setSections(prev => ({
      ...prev,
      [key]: raw.split('\n').map(line => line.trim()).filter(Boolean),
    }));
  };

  const saveTemplate = async () => {
    setSaving(true);
    try {
      await api('/profile/1', { method: 'PUT', body: JSON.stringify({ resume_bullets: sections }) });
      await onRefresh();
    } catch (e) {
      alert(e.message);
    }
    setSaving(false);
  };

  return <div style={s.card}>
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12,gap:12,flexWrap:'wrap'}}>
      <div>
        <h3 style={{...s.h3,margin:0}}>Base resume template</h3>
        <p style={{...s.sub,margin:'6px 0 0'}}>This is the base resume the AI rewrites for each role. You can edit any section before generating a tailored resume.</p>
      </div>
      <button style={s.btn('#1a1a2e', saving)} disabled={saving} onClick={saveTemplate}>{saving ? 'Saving...' : 'Save base template'}</button>
    </div>
    <div style={{display:'flex',gap:8,flexWrap:'wrap',marginBottom:12}}>
      <span style={s.badge('#e8eafc','#4361ee')}>Resume file: {profile?.resume_template_path ? fileName(profile.resume_template_path) : 'none uploaded'}</span>
      <span style={s.badge('#f3e8ff','#6f42c1')}>Cover letter file: {profile?.cover_letter_template_path ? fileName(profile.cover_letter_template_path) : 'none uploaded'}</span>
    </div>
    <div style={s.grid(300)}>
      {Object.entries(sections).map(([key, bullets]) => <div key={key} style={{background:'#f8f9fa',borderRadius:10,padding:14,border:'1px solid #e9ecef'}}>
        <div style={{fontSize:12,fontWeight:700,color:'#1a1a2e',textTransform:'uppercase',letterSpacing:'0.4px',marginBottom:8}}>{SECTION_NAMES[key] || key}</div>
        <textarea
          style={{...s.input,minHeight:140,resize:'vertical',fontSize:12,lineHeight:1.6}}
          value={(bullets || []).join('\n')}
          onChange={e=>updateSection(key, e.target.value)}
        />
      </div>)}
    </div>
  </div>;
}

// ═══ DASHBOARD ═══
function Dashboard({ data, profile, onAction, loading, onRefresh }) {
  const st = data?.applications || {};
  return <div>
    <div style={s.grid(140)}>
      {[{n:data?.total_jobs||0,l:'Jobs found',c:'#4361ee'},{n:st.total||0,l:'Tailored',c:'#6f42c1'},{n:st.submitted||0,l:'Applied',c:'#20c997'},{n:st.callbacks||0,l:'Callbacks',c:'#fd7e14'},{n:st.interviews||0,l:'Interviews',c:'#28a745'},{n:`${st.callback_rate||0}%`,l:'Callback rate',c:'#17a2b8'}].map((x,i) =>
        <div key={i} style={s.stat}><div style={{...s.statN,color:x.c}}>{x.n}</div><div style={s.statL}>{x.l}</div></div>)}
    </div>
    <div style={s.card}>
      <h3 style={s.h3}>One-click pipeline</h3>
      <p style={s.sub}>Runs all 5 steps automatically: Discover → Score → Playbook → Tailor → Generate docs</p>
      <button style={{...s.btn('#1a1a2e', loading.pipeline), padding:'14px 32px', fontSize:15}} disabled={loading.pipeline}
        onClick={()=>onAction('pipeline')}>
        {loading.pipeline ? 'Running full pipeline...' : 'Run full pipeline'}
      </button>
    </div>
    <div style={s.card}>
      <h3 style={s.h3}>Individual steps</h3>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <button style={s.btn('#4361ee', loading.discover)} disabled={loading.discover} onClick={()=>onAction('discover')}>{loading.discover ? 'Discovering...' : '1. Discover'}</button>
        <button style={s.btn('#6f42c1', loading.playbook)} disabled={loading.playbook} onClick={()=>onAction('playbook')}>{loading.playbook ? 'Thinking...' : '2. Playbook'}</button>
        <button style={s.btn('#20c997', loading.tailor)} disabled={loading.tailor} onClick={()=>onAction('tailor')}>{loading.tailor ? 'Tailoring...' : '3. Tailor'}</button>
        <button style={s.btn('#fd7e14', loading.docs)} disabled={loading.docs} onClick={()=>onAction('docs')}>{loading.docs ? 'Generating...' : '4. Gen docs'}</button>
      </div>
    </div>
    {data?.recent_runs?.length > 0 && <div style={s.card}>
      <h3 style={s.h3}>Recent runs</h3>
      {data.recent_runs.map((r,i) => <div key={i} style={{display:'flex',justifyContent:'space-between',padding:'8px 0',borderBottom:'1px solid #f1f3f5',fontSize:13}}>
        <span style={{color:'#6c757d'}}>{r.run_type || 'manual'}</span>
        <span>{r.jobs_discovered||0} found · {r.jobs_new||0} new · {r.jobs_tailored||0} tailored</span>
        <span style={{color:r.status==='completed'?'#28a745':r.status==='failed'?'#dc3545':'#fd7e14',fontWeight:600}}>{r.status}</span>
      </div>)}
    </div>}
    <ProfileAssets profile={profile} onRefresh={onRefresh} />
  </div>;
}

// ═══ JOBS ═══
function Jobs({ jobs, onRefresh }) {
  const [input, setInput] = useState('');
  const [adding, setAdding] = useState(false);
  const [selected, setSelected] = useState(null);
  const [connLoading, setConnLoading] = useState(false);
  const [connResult, setConnResult] = useState(null);

  const addManual = async () => {
    const parsed = input.split('\n').filter(l=>l.trim()).map(l => { const p = l.split('|').map(x=>x.trim()); return {title:p[0]||'',company:p[1]||'',location:p[2]||'',url:p[3]||'',requirements:(p[4]||'').split(',').map(x=>x.trim()).filter(Boolean)}; }).filter(j=>j.title&&j.company);
    if (!parsed.length) return;
    setAdding(true);
    try { const r = await api('/jobs/manual', {method:'POST',body:JSON.stringify(parsed)}); setInput(''); onRefresh(); alert(`Added ${r.inserted} jobs`); }
    catch (e) { alert(e.message); }
    setAdding(false);
  };

  const findConn = async (jid) => {
    setConnLoading(true); setConnResult(null);
    try { const r = await api(`/connections/${jid}`, {method:'POST'}); setConnResult(r); }
    catch (e) { alert(e.message); }
    setConnLoading(false);
  };

  return <div>
    <div style={s.card}>
      <h3 style={s.h3}>Add jobs manually</h3>
      <p style={{fontSize:12,color:'#6c757d',margin:'0 0 8px'}}>Title | Company | Location | URL | Requirements</p>
      <textarea style={{...s.input,minHeight:60,fontFamily:'monospace',fontSize:12}} value={input} onChange={e=>setInput(e.target.value)} placeholder="Strategy Analyst | Google | NYC | https://..." />
      <button style={{...s.btn('#4361ee',adding||!input.trim()),marginTop:8}} disabled={adding||!input.trim()} onClick={addManual}>{adding?'Adding...':'Add jobs'}</button>
    </div>
    <div style={s.card}>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
        <h3 style={{...s.h3,margin:0}}>Job queue ({jobs.length})</h3>
        <button style={s.btnO()} onClick={onRefresh}>Refresh</button>
      </div>
      <div style={{maxHeight:500,overflowY:'auto'}}>
        {jobs.map(j => <div key={j.id} style={{padding:'12px 0',borderBottom:'1px solid #f1f3f5',cursor:'pointer'}} onClick={()=>setSelected(selected===j.id?null:j.id)}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start'}}>
            <div><div style={{fontSize:14,fontWeight:600}}>{j.title}</div><div style={{fontSize:12,color:'#6c757d'}}>{j.company} · {j.location}</div></div>
            <div style={{display:'flex',gap:6,alignItems:'center'}}>
              <ScoreBadge score={j.match_score} />
              {j.archetype && <span style={s.badge('#e8eafc','#4361ee')}>{j.archetype}</span>}
              {j.url && <a href={j.url} target="_blank" rel="noreferrer" onClick={e=>e.stopPropagation()} style={{...s.btnO('#28a745'),fontSize:11,padding:'4px 10px'}}>View</a>}
            </div>
          </div>
          {selected===j.id && <div style={{marginTop:12,padding:12,background:'#f8f9fa',borderRadius:8,fontSize:13}}>
            {j.requirements && <div style={{marginBottom:8}}><strong>Requirements:</strong> {Array.isArray(j.requirements)?j.requirements.join(', '):j.requirements}</div>}
            {j.decision_maker && <div style={{marginBottom:8}}><strong>Decision maker:</strong> {j.decision_maker}</div>}
            <button style={s.btnO('#6f42c1')} onClick={e=>{e.stopPropagation();findConn(j.id)}}>{connLoading?'Finding...':'Find decision maker'}</button>
            {connResult && selected===j.id && <div style={{marginTop:12,padding:12,background:'#fff',borderRadius:8,border:'1px solid #e9ecef'}}>
              <div style={{fontSize:13,fontWeight:600,marginBottom:6}}>{connResult.contact_title}</div>
              {connResult.outreach_message ? <div style={{fontSize:12,color:'#495057',lineHeight:1.6,whiteSpace:'pre-wrap'}}>{connResult.outreach_message}</div> : <div style={{fontSize:12,color:'#adb5bd'}}>Generating message...</div>}
            </div>}
          </div>}
        </div>)}
        {!jobs.length && <p style={{color:'#adb5bd',fontSize:13,textAlign:'center',padding:20}}>No jobs yet. Run discovery or add manually.</p>}
      </div>
    </div>
  </div>;
}

// ═══ RESUME STUDIO ═══
function ResumeStudio({ applications, profile, onRefresh }) {
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [generating, setGenerating] = useState(null);

  const loadDetail = async (aid) => {
    if (selected === aid) { setSelected(null); setDetail(null); return; }
    setSelected(aid);
    try { const d = await api(`/applications/${aid}`); setDetail(d); }
    catch { setDetail(null); }
  };

  const genDoc = async (aid) => {
    setGenerating(aid);
    try { const r = await api(`/generate-docs/${aid}`, {method:'POST'}); alert(`Resume generated: ${r.filename}`); }
    catch (e) { alert(e.message); }
    setGenerating(null);
  };

  const hasBullets = (tb) => {
    if (!tb || typeof tb !== 'object') return false;
    return Object.values(tb).some(v => Array.isArray(v) && v.length > 0 && v.some(b => b && b.length > 10));
  };

  const baseSections = normalizeResumeBullets(profile?.resume_bullets);

  return <div>
    <BaseResumeEditor profile={profile} onRefresh={onRefresh} />
    <div style={s.card}>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
        <h3 style={{...s.h3,margin:0}}>Tailored applications ({applications.length})</h3>
        <div style={{display:'flex',gap:6}}>
          <span style={s.badge('#d4edda','#155724')}>{applications.filter(a=>hasBullets(a.tailored_bullets)).length} with content</span>
          <span style={s.badge('#f8d7da','#721c24')}>{applications.filter(a=>!hasBullets(a.tailored_bullets)).length} pending</span>
        </div>
      </div>
      <div style={{maxHeight:600,overflowY:'auto'}}>
        {applications.map(a => {
          const hasContent = hasBullets(a.tailored_bullets);
          return <div key={a.id} style={{padding:'12px 0',borderBottom:'1px solid #f1f3f5'}}>
            <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',cursor:'pointer'}} onClick={()=>loadDetail(a.id)}>
              <div>
                <div style={{fontSize:14,fontWeight:600}}>{a.title} <span style={{fontWeight:400,color:'#6c757d'}}>at {a.company}</span></div>
                <div style={{display:'flex',gap:6,marginTop:4}}>
                  {a.archetype && a.archetype !== 'Unknown' && <span style={s.badge('#e8eafc','#4361ee')}>{a.archetype}</span>}
                  <StatusBadge status={a.apply_status} />
                  <OutcomeBadge outcome={a.outcome} />
                  {hasContent && <span style={s.badge('#d4edda','#155724')}>tailored</span>}
                  {a.resume_path && a.resume_path.endsWith('.docx') && <span style={s.badge('#cce5ff','#004085')}>.docx ready</span>}
                </div>
              </div>
              <div style={{display:'flex',gap:6}}>
                {hasContent && <button style={s.btnO('#4361ee')} onClick={e=>{e.stopPropagation();genDoc(a.id)}}>{generating===a.id?'...':'Generate .docx'}</button>}
                <span style={{fontSize:20,color:'#6c757d'}}>{selected===a.id?'−':'+'}</span>
              </div>
            </div>
            {selected===a.id && detail && <div style={{marginTop:16}}>
              <div style={{background:'#fff',borderRadius:12,padding:16,border:'1px solid #e9ecef',marginBottom:12,display:'flex',justifyContent:'space-between',alignItems:'center',gap:12,flexWrap:'wrap'}}>
                <div>
                  <div style={{fontSize:13,fontWeight:700,color:'#1a1a2e',marginBottom:4}}>Generated files</div>
                  <div style={{fontSize:12,color:'#6c757d'}}>
                    {detail.resume_path ? fileName(detail.resume_path) : 'No tailored resume file generated yet'}
                  </div>
                </div>
                <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
                  {detail.resume_path && <a href={fileUrl(`/applications/${a.id}/resume-file`)} target="_blank" rel="noreferrer" style={s.btnO('#1a1a2e')}>Open resume</a>}
                  {detail.cover_letter_path && <a href={fileUrl(`/applications/${a.id}/cover-letter-file`)} target="_blank" rel="noreferrer" style={s.btnO('#6f42c1')}>Open cover letter</a>}
                </div>
              </div>
              <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit, minmax(300px, 1fr))',gap:12,marginBottom:12}}>
                <div style={{background:'#f8f9fa',borderRadius:12,padding:20}}>
                  <h4 style={{fontSize:14,fontWeight:700,color:'#1a1a2e',margin:'0 0 16px',borderBottom:'2px solid #1a1a2e20',paddingBottom:8}}>Base resume template</h4>
                  {Object.entries(baseSections).map(([sec, bullets]) =>
                    <div key={sec} style={{marginBottom:16}}>
                      <div style={{fontSize:12,fontWeight:700,color:'#1a1a2e',textTransform:'uppercase',letterSpacing:'0.5px',marginBottom:6,background:'#edf2f7',padding:'4px 10px',borderRadius:4,display:'inline-block'}}>{SECTION_NAMES[sec]||sec}</div>
                      {bullets.map((b,i) => <p key={i} style={{fontSize:13,lineHeight:1.6,margin:'6px 0',paddingLeft:14,borderLeft:'3px solid #adb5bd',color:'#495057'}}>{b}</p>)}
                    </div>
                  )}
                </div>
                <div style={{background:'#f8f9fa',borderRadius:12,padding:20}}>
                  <h4 style={{fontSize:14,fontWeight:700,color:'#4361ee',margin:'0 0 16px',borderBottom:'2px solid #4361ee30',paddingBottom:8}}>Tailored resume output</h4>
                  {detail.tailored_bullets && typeof detail.tailored_bullets === 'object' ? (
                    Object.entries(detail.tailored_bullets).filter(([,v])=>Array.isArray(v)&&v.length>0).length > 0 ? (
                      Object.entries(detail.tailored_bullets).filter(([,v])=>Array.isArray(v)&&v.length>0).map(([sec,bullets]) =>
                        <div key={sec} style={{marginBottom:16}}>
                          <div style={{fontSize:12,fontWeight:700,color:'#1a1a2e',textTransform:'uppercase',letterSpacing:'0.5px',marginBottom:6,background:'#e8eafc',padding:'4px 10px',borderRadius:4,display:'inline-block'}}>{SECTION_NAMES[sec]||sec}</div>
                          {bullets.map((b,i) => <p key={i} style={{fontSize:13,lineHeight:1.6,margin:'6px 0',paddingLeft:14,borderLeft:'3px solid #4361ee40',color:'#2c2c2c'}}>{b}</p>)}
                        </div>)
                    ) : <p style={{color:'#adb5bd',fontSize:13}}>Bullets not yet generated. Run the pipeline again.</p>
                  ) : <p style={{color:'#adb5bd',fontSize:13}}>No tailored content available.</p>}
                </div>
              </div>
              {/* Cover letter */}
              <div style={{background:'#f8f9fa',borderRadius:12,padding:20}}>
                <h4 style={{fontSize:14,fontWeight:700,color:'#6f42c1',margin:'0 0 12px',borderBottom:'2px solid #6f42c130',paddingBottom:8}}>Cover letter</h4>
                {detail.cover_letter && detail.cover_letter !== 'Not generated yet' ? (
                  detail.cover_letter.split('\n').filter(p=>p.trim()).map((para,i) =>
                    <p key={i} style={{fontSize:13,lineHeight:1.7,margin:'0 0 12px',color:'#2c2c2c'}}>{para}</p>)
                ) : <p style={{color:'#adb5bd',fontSize:13}}>Cover letter not yet generated.</p>}
              </div>
            </div>}
          </div>;
        })}
        {!applications.length && <p style={{color:'#adb5bd',fontSize:13,textAlign:'center',padding:20}}>No tailored applications yet. Run the pipeline.</p>}
      </div>
    </div>
  </div>;
}

// ═══ AUTO-APPLY ═══
function AutoApply({ applications }) {
  const pending = applications.filter(a => a.apply_status === 'pending' && a.tailored_bullets);
  const submitted = applications.filter(a => a.apply_status === 'submitted' || a.apply_status === 'ready_to_submit');

  return <div>
    <div style={s.card}>
      <div style={{background:'#e8eafc',borderRadius:8,padding:14,marginBottom:16,fontSize:13,color:'#3c3489',lineHeight:1.6}}>
        <strong>How auto-apply works:</strong> The web dashboard manages your application queue. Actual form-filling runs from your local machine using the CLI script with your real browser, so career pages don't detect cloud IPs.
        <pre style={{background:'#fff',padding:10,borderRadius:6,marginTop:8,fontSize:11,overflowX:'auto'}}>python rpa_local.py --server http://167.172.116.247 --limit 10 --dry-run</pre>
      </div>
      <h3 style={s.h3}>Ready to apply ({pending.length})</h3>
      {pending.slice(0,20).map(a => <div key={a.id} style={{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'10px 0',borderBottom:'1px solid #f1f3f5'}}>
        <div><div style={{fontSize:13,fontWeight:600}}>{a.title}</div><div style={{fontSize:11,color:'#6c757d'}}>{a.company} · {a.location}</div></div>
        <div style={{display:'flex',gap:6}}>
          {a.resume_path && a.resume_path.endsWith('.docx') && <span style={s.badge('#d4edda','#155724')}>.docx</span>}
          {a.url && <a href={a.url} target="_blank" rel="noreferrer" style={s.btnO('#28a745')}>Open page</a>}
        </div>
      </div>)}
      {!pending.length && <p style={{color:'#adb5bd',fontSize:13}}>All caught up. Run the pipeline to discover more jobs.</p>}
    </div>
    {submitted.length > 0 && <div style={s.card}>
      <h3 style={s.h3}>Submitted ({submitted.length})</h3>
      {submitted.map(a => <div key={a.id} style={{display:'flex',justifyContent:'space-between',padding:'8px 0',borderBottom:'1px solid #f1f3f5',fontSize:13}}>
        <span>{a.title} at {a.company}</span><StatusBadge status={a.apply_status} />
      </div>)}
    </div>}
  </div>;
}

// ═══ ANALYTICS ═══
function Analytics({ data, applications, onRefresh }) {
  const [updating, setUpdating] = useState(null);
  const updateOutcome = async (aid, outcome) => {
    setUpdating(aid);
    try { await api('/outcome', {method:'POST',body:JSON.stringify({application_id:aid,outcome})}); onRefresh(); }
    catch (e) { alert(e.message); }
    setUpdating(null);
  };
  const outcomes = ['callback','interview','offer','rejected','ghosted'];

  return <div>
    <div style={s.grid(200)}>
      {data?.archetypes && Object.entries(data.archetypes).map(([arch,d]) =>
        <div key={arch} style={s.stat}>
          <div style={{fontSize:13,fontWeight:700,marginBottom:6}}>{arch}</div>
          <div style={{fontSize:11,color:'#6c757d'}}>{d.total} apps · {d.callback_rate}% callback · {d.interview_rate}% interview</div>
        </div>)}
    </div>
    {data?.variants?.length > 0 && <div style={s.card}>
      <h3 style={s.h3}>A/B test results</h3>
      {data.variants.map((v,i) => <div key={i} style={{display:'flex',justifyContent:'space-between',padding:'8px 0',borderBottom:'1px solid #f1f3f5',fontSize:13}}>
        <span>Variant {v.variant}: {v.description}</span>
        <span style={{color:'#28a745',fontWeight:600}}>{v.success_rate}% success (n={v.total})</span>
      </div>)}
    </div>}
    <div style={s.card}>
      <h3 style={s.h3}>Update outcomes</h3>
      <p style={s.sub}>Track responses to improve future tailoring.</p>
      {applications.filter(a=>a.outcome==='unknown'||a.apply_status==='submitted').slice(0,30).map(a =>
        <div key={a.id} style={{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'8px 0',borderBottom:'1px solid #f1f3f5'}}>
          <div style={{fontSize:13,flex:1}}>{a.title} <span style={{color:'#6c757d'}}>at {a.company}</span></div>
          <div style={{display:'flex',gap:4}}>{outcomes.map(o =>
            <button key={o} onClick={()=>updateOutcome(a.id,o)} disabled={updating===a.id}
              style={{padding:'4px 8px',fontSize:10,fontWeight:600,border:'1px solid #dee2e6',borderRadius:6,
                background:a.outcome===o?'#e8eafc':'transparent',color:o==='offer'||o==='interview'?'#28a745':o==='callback'?'#4361ee':'#dc3545',cursor:'pointer'}}>{o}</button>
          )}</div>
        </div>)}
    </div>
  </div>;
}

// ═══ MAIN APP ═══
export default function App() {
  const [page, setPage] = useState('dashboard');
  const [data, setData] = useState(null);
  const [profile, setProfile] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [apps, setApps] = useState([]);
  const [analyticsData, setAnalytics] = useState(null);
  const [loading, setLoading] = useState({});
  const [status, setStatus] = useState('');
  const [needsOnboarding, setNeedsOnboarding] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const [d,p,j,a,an] = await Promise.all([api('/dashboard'),api('/profile'),api('/jobs?limit=200'),api('/applications?limit=200'),api('/analytics')]);
      setData(d); setProfile(p); setJobs(j); setApps(a); setAnalytics(an); setNeedsOnboarding(!d.profile_exists);
    } catch (e) { console.error(e); setNeedsOnboarding(true); }
  }, []);

  useEffect(() => { refresh(); const i = setInterval(refresh, 15000); return () => clearInterval(i); }, [refresh]);

  const action = async (type) => {
    setLoading(p => ({...p, [type]: true})); setStatus('');
    try {
      if (type === 'pipeline') { const r = await api('/pipeline', {method:'POST'}); setStatus(`Full pipeline started (${r.run_id}). Steps: ${r.steps.join(' → ')}`); }
      else if (type === 'discover') { const r = await api('/discover', {method:'POST'}); setStatus(`Discovery started: ${r.run_id}`); }
      else if (type === 'playbook') { const r = await api('/playbook', {method:'POST'}); setStatus(`Playbook ready: ${r.jobs} jobs analyzed`); }
      else if (type === 'tailor') { const r = await api('/tailor', {method:'POST'}); setStatus(`Tailored ${r.tailored} resumes`); }
      else if (type === 'docs') { const r = await api('/docs-batch', {method:'POST'}); setStatus(`Generated ${r.generated} documents`); }
      setTimeout(refresh, 3000);
    } catch (e) { setStatus(`Error: ${e.message}`); }
    setLoading(p => ({...p, [type]: false}));
  };

  if (needsOnboarding === null) return <div style={{...s.page,display:'flex',alignItems:'center',justifyContent:'center'}}><p>Loading...</p></div>;
  if (needsOnboarding) return <div style={s.page}><Onboarding onComplete={()=>{setNeedsOnboarding(false);refresh()}} /></div>;

  const pages = ['dashboard','jobs','resumes','apply','analytics'];
  return <div style={s.page}>
    <div style={s.nav}>
      <span style={s.logo}>AutoApply</span>
      <div style={s.tabs}>{pages.map(p => <button key={p} style={s.tab(page===p)} onClick={()=>setPage(p)}>{p.charAt(0).toUpperCase()+p.slice(1)}</button>)}</div>
      <div style={{fontSize:12,color:'#6c757d'}}>{data?.total_jobs||0} jobs · {data?.applications?.total||0} apps</div>
    </div>
    {status && <div style={{margin:'16px 24px 0',padding:'10px 16px',background:status.includes('Error')?'#f8d7da':'#d4edda',borderRadius:8,fontSize:13,color:status.includes('Error')?'#721c24':'#155724'}}>{status}</div>}
    <div style={{padding:'20px 24px',maxWidth:1000,margin:'0 auto'}}>
      {page==='dashboard' && <Dashboard data={data} profile={profile} onAction={action} loading={loading} onRefresh={refresh} />}
      {page==='jobs' && <Jobs jobs={jobs} onRefresh={refresh} />}
      {page==='resumes' && <ResumeStudio applications={apps} profile={profile} onRefresh={refresh} />}
      {page==='apply' && <AutoApply applications={apps} />}
      {page==='analytics' && <Analytics data={analyticsData} applications={apps} onRefresh={refresh} />}
    </div>
  </div>;
}
