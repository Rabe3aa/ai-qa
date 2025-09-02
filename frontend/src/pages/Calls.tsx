import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getCalls, getProjects, exportCalls } from '../api/client';
import type { Call, Project } from '../types';
import UploadModal from '../components/UploadModal';

export default function Calls() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState<number | ''>('');
  const [status, setStatus] = useState<string>('');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [agent, setAgent] = useState<string>('');
  const [q, setQ] = useState<string>('');
  const [calls, setCalls] = useState<Call[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const navigate = useNavigate();

  useEffect(() => { (async () => {
    try {
      const ps = await getProjects();
      setProjects(ps);
      if (ps.length > 0) setProjectId(ps[0].id);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load projects');
    }
  })(); }, []);

  function isoStart(d: string) { return d ? `${d}T00:00:00Z` : undefined; }
  function isoEnd(d: string) { return d ? `${d}T23:59:59Z` : undefined; }

  async function loadCalls() {
    if (projectId === '') return;
    setLoading(true);
    try {
      const data = await getCalls({
        project_id: projectId as number,
        status: status || undefined,
        start_date: isoStart(dateFrom),
        end_date: isoEnd(dateTo),
        agent: agent || undefined,
        q: q || undefined,
        limit: 100,
      });
      setCalls(data);
      setError(null);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load calls');
    } finally { setLoading(false); }
  }

  useEffect(() => { if (projectId !== '') loadCalls(); }, [projectId, status, dateFrom, dateTo, agent, q]);

  const statusOptions = useMemo(() => ([
    { value: '', label: 'All' },
    { value: 'uploaded', label: 'Uploaded' },
    { value: 'processing', label: 'Processing' },
    { value: 'completed', label: 'Completed' },
    { value: 'failed', label: 'Failed' },
  ]), []);

  return (
    <div>
      <h1>Calls</h1>

      <div className="card" style={{marginBottom:16}}>
        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr 1fr 1fr 1fr 1fr auto auto', gap:12}}>
          <div>
            <label>Project</label>
            <select value={projectId} onChange={e=>setProjectId(e.target.value ? Number(e.target.value) : '')}>
              <option value="">Select project</option>
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div>
            <label>Status</label>
            <select value={status} onChange={e=>setStatus(e.target.value)}>
              {statusOptions.map(o=> <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div>
            <label>From</label>
            <input type="date" value={dateFrom} onChange={e=>setDateFrom(e.target.value)} />
          </div>
          <div>
            <label>To</label>
            <input type="date" value={dateTo} onChange={e=>setDateTo(e.target.value)} />
          </div>
          <div>
            <label>Agent</label>
            <input type="text" placeholder="Agent name" value={agent} onChange={e=>setAgent(e.target.value)} />
          </div>
          <div>
            <label>Search</label>
            <input type="text" placeholder="Filename, customer..." value={q} onChange={e=>setQ(e.target.value)} />
          </div>
          <div>
            <label>&nbsp;</label>
            <button className="button secondary" onClick={loadCalls}>Refresh</button>
          </div>
          <div style={{textAlign:'right'}}>
            <label>&nbsp;</label>
            <button className="button secondary" onClick={async ()=>{
              if (projectId === '') return;
              try {
                const blob = await exportCalls({
                  project_id: projectId as number,
                  status: status || undefined,
                  start_date: isoStart(dateFrom),
                  end_date: isoEnd(dateTo),
                  agent: agent || undefined,
                  q: q || undefined,
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = `calls_${new Date().toISOString().slice(0,10)}.csv`;
                document.body.appendChild(a); a.click(); a.remove();
                URL.revokeObjectURL(url);
              } catch (e) { /* noop */ }
            }}>Export CSV</button>
            <span style={{marginLeft:8}}/>
            <button className="button" onClick={()=>setShowUpload(true)}>Upload Call</button>
          </div>
        </div>
      </div>

      {loading ? <div>Loading calls...</div> : error ? (
        <div style={{color:'var(--danger)'}}>{error}</div>
      ) : (
        <div className="card">
          <table>
            <thead>
              <tr>
                <th style={{textAlign:'left'}}>Filename</th>
                <th>Agent</th>
                <th>Status</th>
                <th>Uploaded</th>
                <th>Processed</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {calls.map(c => (
                <tr key={c.id}>
                  <td style={{textAlign:'left'}}>{c.filename}</td>
                  <td>{c.agent_name || '-'}</td>
                  <td>{c.status}</td>
                  <td>{new Date(c.uploaded_at).toLocaleString()}</td>
                  <td>{c.processed_at ? new Date(c.processed_at).toLocaleString() : '-'}</td>
                  <td style={{textAlign:'right'}}>
                    <button className="button secondary" onClick={()=>navigate(`/calls/${c.id}`)}>View</button>
                  </td>
                </tr>
              ))}
              {calls.length === 0 && (
                <tr><td colSpan={6} style={{textAlign:'center', color:'var(--muted)'}}>No calls</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <UploadModal
        open={showUpload}
        onClose={() => setShowUpload(false)}
        projects={projects}
        defaultProjectId={projectId || undefined}
        onUploaded={() => loadCalls()}
      />
    </div>
  );
}
