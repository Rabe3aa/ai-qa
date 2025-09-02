import { useEffect, useState } from 'react';
import { analyzeCall, createUploadUrl, uploadToPresignedUrl } from '../api/client';
import type { Project } from '../types';

interface Props {
  open: boolean;
  onClose: () => void;
  projects: Project[];
  defaultProjectId?: number;
  onUploaded?: (callId: number) => void;
}

export default function UploadModal({ open, onClose, projects, defaultProjectId, onUploaded }: Props) {
  const [projectId, setProjectId] = useState<number | ''>(defaultProjectId ?? '');
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      setProjectId(defaultProjectId ?? '');
      setFile(null);
      setStatus(null);
      setError(null);
      setBusy(false);
    }
  }, [open, defaultProjectId]);

  if (!open) return null;

  async function startUpload() {
    if (!file || !projectId) { setError('Select project and file'); return; }
    setBusy(true); setError(null); setStatus('Requesting upload URL...');
    try {
      const content_type = file.type || 'application/octet-stream';
      const { upload_url, call_id } = await createUploadUrl(projectId as number, { filename: file.name, content_type });
      setStatus('Uploading to S3...');
      await uploadToPresignedUrl(upload_url, file);
      setStatus('Starting analysis...');
      await analyzeCall(call_id);
      setStatus('Upload and analysis started');
      onUploaded?.(call_id);
      setTimeout(onClose, 800);
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || 'Upload failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e=>e.stopPropagation()}>
        <h2>Upload Call</h2>
        <div style={{marginTop:12}}>
          <label>Project</label>
          <select value={projectId} onChange={e=>setProjectId(e.target.value ? Number(e.target.value) : '')}>
            <option value="">Select project</option>
            {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div style={{marginTop:12}}>
          <label>Audio File</label>
          <input type="file" accept="audio/*" onChange={e=>setFile(e.target.files?.[0] || null)} />
        </div>
        {status && <div style={{marginTop:12, color:'#22c55e'}}>{status}</div>}
        {error && <div style={{marginTop:12, color:'var(--danger)'}}>{error}</div>}
        <div className="actions" style={{marginTop:16}}>
          <button className="button" disabled={busy} onClick={startUpload}>{busy ? 'Working...' : 'Upload & Analyze'}</button>
          <button className="button secondary" onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
