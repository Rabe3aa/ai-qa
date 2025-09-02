# QA System Frontend (Vite + React + TS)

- Dev server: http://localhost:3000
- API base URL is set via `VITE_API_BASE_URL`

## Setup
1. Install Node.js 18+.
2. `cd frontend`
3. `npm install`
4. Create `.env.development` with:
```
VITE_API_BASE_URL=http://localhost:8000
```
5. `npm run dev`

Login with your admin credentials, then view Dashboard and Projects.

## Deploy
- Build: `npm run build`
- Serve `dist/` via any static host or integrate into your infra.
- For production, set `VITE_API_BASE_URL` to your App Runner backend URL.
