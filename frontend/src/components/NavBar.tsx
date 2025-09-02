import { NavLink, useNavigate } from 'react-router-dom';
import { clearToken, getToken } from '../auth';

export default function NavBar() {
  const navigate = useNavigate();
  const authed = !!getToken();
  return (
    <div className="nav">
      <div className="links">
        <NavLink to="/dashboard" className={({isActive}) => isActive ? 'active' : ''}>Dashboard</NavLink>
        <NavLink to="/projects" className={({isActive}) => isActive ? 'active' : ''}>Projects</NavLink>
        <NavLink to="/calls" className={({isActive}) => isActive ? 'active' : ''}>Calls</NavLink>
      </div>
      <div>
        {authed ? (
          <button className="button secondary" onClick={() => { clearToken(); navigate('/login'); }}>Logout</button>
        ) : null}
      </div>
    </div>
  );
}
