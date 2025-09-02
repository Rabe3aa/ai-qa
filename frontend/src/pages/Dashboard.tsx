import { useEffect, useState } from 'react';
import { getAgentPerformance, getDashboardStats, getProjects, exportAgentPerformance } from '../api/client';
import type { DashboardStats, AgentPerformance, Project } from '../types';

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState<number | undefined>(undefined);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [agents, setAgents] = useState<AgentPerformance[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [agent, setAgent] = useState<string>('');

  useEffect(() => {
    (async () => {
      try {
        const ps = await getProjects();
        setProjects(ps);
        if (ps.length > 0) setProjectId(ps[0].id);
      } catch (e: any) {
        setErr(e?.response?.data?.detail || 'Failed to load initial data');
      }
    })();
  }, []);

  function isoStart(d: string) { return d ? `${d}T00:00:00Z` : undefined; }
  function isoEnd(d: string) { return d ? `${d}T23:59:59Z` : undefined; }

  useEffect(() => {
    if (projectId === undefined && projects.length === 0) return;
    setLoading(true);
    (async () => {
      try {
        const [s, a] = await Promise.all([
          getDashboardStats({ project_id: projectId, start_date: isoStart(dateFrom), end_date: isoEnd(dateTo) }),
          getAgentPerformance({ project_id: projectId, start_date: isoStart(dateFrom), end_date: isoEnd(dateTo), agent: agent || undefined }),
        ]);
        setStats(s); setAgents(a); setErr(null);
      } catch (e: any) {
        setErr(e?.response?.data?.detail || 'Failed to load dashboard');
      } finally {
        setLoading(false);
      }
    })();
  }, [projectId, projects.length, dateFrom, dateTo, agent]);

  const total = stats?.total_calls ?? 0;
  const processed = stats?.processed_calls ?? 0;
  const pending = stats?.pending_calls ?? 0;
  const failed = stats?.failed_calls ?? 0;
  const avg = stats?.average_score ?? null;
  const totalTime = stats?.total_processing_time ?? null;

  return (
    <div>
      <h1>Dashboard</h1>
      <div className="card" style={{marginBottom:16}}>
        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr 1fr 1fr auto', gap:12}}>
          <div>
            <label>Project</label>
            <select value={projectId ?? ''} onChange={e=>setProjectId(e.target.value ? Number(e.target.value) : undefined)}>
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
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
            <label>&nbsp;</label>
            <div>
              <button className="button secondary" onClick={()=>{
                // trigger useEffect
                setDateFrom(dateFrom);
              }}>Refresh</button>
              <span style={{marginLeft:8}}/>
              <button className="button" onClick={async ()=>{
                try {
                  const blob = await exportAgentPerformance({ project_id: projectId, start_date: isoStart(dateFrom), end_date: isoEnd(dateTo), agent: agent || undefined });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url; a.download = `agent_performance_${new Date().toISOString().slice(0,10)}.csv`;
                  document.body.appendChild(a); a.click(); a.remove();
                  URL.revokeObjectURL(url);
                } catch(e) { /* noop */ }
              }}>Export CSV</button>
            </div>
          </div>
        </div>
      </div>

      {loading ? <div>Loading...</div> : err ? <div style={{color:'var(--danger)'}}>{err}</div> : (
        <>
          <div className="card-grid">
            <div className="card"><h2>Total Calls</h2><div style={{fontSize:28, fontWeight:700}}>{total}</div></div>
            <div className="card"><h2>Processed</h2><div style={{fontSize:28, fontWeight:700}}>{processed}</div></div>
            <div className="card"><h2>Pending</h2><div style={{fontSize:28, fontWeight:700}}>{pending}</div></div>
            <div className="card"><h2>Failed</h2><div style={{fontSize:28, fontWeight:700}}>{failed}</div></div>
            <div className="card"><h2>Average Score</h2><div style={{fontSize:28, fontWeight:700}}>{avg !== null ? avg.toFixed(2) : '-'}</div></div>
            <div className="card"><h2>Total Proc. Time</h2><div style={{fontSize:28, fontWeight:700}}>{totalTime !== null ? `${totalTime}s` : '-'}</div></div>
          </div>

          <div className="card" style={{marginTop:16}}>
            <h2>Agent Performance</h2>
            <table>
              <thead><tr><th style={{textAlign:'left'}}>Agent</th><th>Total Calls</th><th>Avg Score</th><th>Recent Calls</th></tr></thead>
              <tbody>
                {agents.map(a => (
                  <tr key={a.agent_name}>
                    <td style={{textAlign:'left'}}>{a.agent_name}</td>
                    <td>{a.total_calls}</td>
                    <td>{a.average_score !== null ? a.average_score.toFixed(2) : '-'}</td>
                    <td>{a.recent_calls}</td>
                  </tr>
                ))}
                {agents.length === 0 && (
                  <tr><td colSpan={4} style={{textAlign:'center', color:'var(--muted)'}}>No data</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
