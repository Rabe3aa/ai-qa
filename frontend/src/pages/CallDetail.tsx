import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { analyzeCall, getCall, getCallReport } from '../api/client';
import type { Call, QAReport } from '../types';

export default function CallDetail() {
  const { id } = useParams();
  const callId = Number(id);
  const [call, setCall] = useState<Call | null>(null);
  const [report, setReport] = useState<QAReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const c = await getCall(callId);
      setCall(c);
      try {
        const r = await getCallReport(callId);
        setReport(r);
      } catch (e: any) {
        // 404 => no report yet
        setReport(null);
      }
      setError(null);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to load call');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { if (!isNaN(callId)) load(); }, [callId]);

  async function startAnalyze() {
    setBusy(true);
    try {
      await analyzeCall(callId);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to start analysis');
    } finally { setBusy(false); }
  }

  if (loading) return <div>Loading...</div>;
  if (error) return <div style={{color:'var(--danger)'}}>{error}</div>;
  if (!call) return <div>Not found</div>;

  return (
    <div>
      <div style={{display:'flex', alignItems:'center', justifyContent:'space-between'}}>
        <h1>Call Detail</h1>
        <Link to="/calls" className="button secondary">Back to Calls</Link>
      </div>

      <div className="card" style={{marginBottom:16}}>
        <h2>Metadata</h2>
        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:12}}>
          <div><label>Filename</label><div>{call.filename}</div></div>
          <div><label>Status</label><div>{call.status}</div></div>
          <div><label>Agent</label><div>{call.agent_name || '-'}</div></div>
          <div><label>Uploaded</label><div>{new Date(call.uploaded_at).toLocaleString()}</div></div>
          <div><label>Processed</label><div>{call.processed_at ? new Date(call.processed_at).toLocaleString() : '-'}</div></div>
          <div><label>Duration</label><div>{call.call_duration ? `${call.call_duration}s` : '-'}</div></div>
        </div>
        <div style={{marginTop:12, display:'flex', gap:8}}>
          {(call.status === 'uploaded' || call.status === 'failed') && (
            <button className="button" disabled={busy} onClick={startAnalyze}>{busy ? 'Starting...' : 'Start Analysis'}</button>
          )}
          <button className="button secondary" onClick={load}>Refresh</button>
        </div>
        {call.error_message && <div style={{color:'var(--danger)', marginTop:8}}>Error: {call.error_message}</div>}
      </div>

      <div className="card">
        <h2>QA Report</h2>
        {!report ? (
          <div style={{color:'var(--muted)'}}>No report yet.</div>
        ) : (
          <>
            <div style={{display:'grid', gridTemplateColumns:'1fr 1fr 1fr 1fr', gap:12}}>
              <div><label>Overall Score</label><div style={{fontSize:24, fontWeight:700}}>{report.overall_score ?? '-'}</div></div>
              <div><label>Positive</label><div>{report.positive_count}</div></div>
              <div><label>Negative</label><div>{report.negative_count}</div></div>
              <div><label>Neutral</label><div>{report.neutral_count}</div></div>
            </div>
            {report.agent_summary && (
              <div style={{marginTop:12}}>
                <label>Agent Summary</label>
                <div style={{whiteSpace:'pre-wrap'}}>{report.agent_summary}</div>
              </div>
            )}
            {report.qa_feedback && (
              <div style={{marginTop:12}}>
                <label>QA Feedback</label>
                <div style={{whiteSpace:'pre-wrap'}}>{report.qa_feedback}</div>
              </div>
            )}
            {report.qa_scores && (
              <div style={{marginTop:12}}>
                <label>QA Scores</label>
                <table>
                  <tbody>
                    {Object.entries(report.qa_scores).map(([k,v]) => (
                      <tr key={k}>
                        <td style={{textAlign:'left', width:'30%'}}>{k}</td>
                        <td>{String(v)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {report.corrected_transcript && (
              <div style={{marginTop:12}}>
                <label>Corrected Transcript</label>
                <div style={{whiteSpace:'pre-wrap', maxHeight:300, overflow:'auto', padding:12, background:'#0b1220', border:'1px solid #253042', borderRadius:8}}>
                  {report.corrected_transcript}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
