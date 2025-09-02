import { useEffect, useState } from 'react';
import { getProjects } from '../api/client';
import type { Project } from '../types';

export default function Projects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await getProjects();
        setProjects(data);
      } catch (e: any) {
        setError(e?.response?.data?.detail || 'Failed to load projects');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <div>Loading projects...</div>;
  if (error) return <div style={{ color: 'var(--danger)' }}>{error}</div>;

  return (
    <div>
      <h1>Projects</h1>
      <div className="card">
        <table>
          <thead>
            <tr>
              <th style={{textAlign:'left'}}>Name</th>
              <th>Description</th>
              <th>Active</th>
            </tr>
          </thead>
          <tbody>
            {projects.map(p => (
              <tr key={p.id}>
                <td style={{textAlign:'left'}}>{p.name}</td>
                <td>{p.description || '-'}</td>
                <td>{p.is_active ? 'Yes' : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
