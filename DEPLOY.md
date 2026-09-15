# SYNTERA — Deployment Guide

This guide gets you from zero to a live, publicly accessible SYNTERA stack:

- **GitHub** — source repo
- **Render** — backend API (FastAPI + Qdrant)
- **Vercel** — frontend (React/Vite)

---

## Prerequisites

Install these once:

| Tool | Download |
|------|----------|
| Git | https://git-scm.com/download/win |
| GitHub CLI | https://cli.github.com/ |
| Node.js 20+ | https://nodejs.org/ |

After installing, open a **new** PowerShell terminal.

---

## Step 1 — Push to GitHub

Run `deploy.ps1` from the repo root (it does everything):

```powershell
cd C:\Users\Raghavendra\SYNTERA
.\deploy.ps1
```

This will:
1. Initialize git
2. Create a `.gitignore`-safe commit (`.env` is excluded)
3. Authenticate with GitHub (`gh auth login` will open a browser)
4. Create the public repo `syntera` under your account
5. Push everything and print the repo URL

**Your GitHub URL:** `https://github.com/<YOUR_USERNAME>/syntera`

---

## Step 2 — Deploy Backend on Render

1. Go to **https://render.com** → sign up / log in with GitHub
2. Click **New → Blueprint** (uses `render.yaml` automatically)
3. Connect your `syntera` GitHub repo
4. Render detects `render.yaml` and creates the `syntera-backend` service
5. In the service's **Environment** tab, add these secret values:

| Key | Value |
|-----|-------|
| `LLM_API_KEY` | your OpenAI API key (`sk-...`) |
| `QDRANT_URL` | leave blank (uses local disk) |
| `QDRANT_API_KEY` | leave blank |

6. Click **Deploy** — takes ~3–5 minutes on first build

**Your backend URL:** `https://syntera-backend.onrender.com`

Health check: `https://syntera-backend.onrender.com/api/health`
API docs: `https://syntera-backend.onrender.com/api/docs`

---

## Step 3 — Deploy Frontend on Vercel

1. Go to **https://vercel.com** → sign up / log in with GitHub
2. Click **Add New → Project**
3. Import your `syntera` GitHub repo
4. Set these settings:
   - **Root Directory:** `frontend`
   - **Framework Preset:** Vite (auto-detected)
   - **Build Command:** `npm install --legacy-peer-deps && npm run build`
   - **Output Directory:** `dist`
5. Add this environment variable:
   - `VITE_API_URL` = _(leave blank — handled by vercel.json rewrites)_
6. Click **Deploy** — takes ~1–2 minutes

**Your frontend URL:** `https://syntera.vercel.app`

> **Note:** After deploy, go to `frontend/vercel.json` and replace
> `https://syntera-backend.onrender.com` with your actual Render URL if it differs,
> then push to trigger a Vercel redeploy.

---

## Step 4 — Update CORS (if your Vercel URL is different)

If Vercel assigns a URL other than `syntera.vercel.app`, open
`backend/app/main.py` and add your URL to the `allow_origins` list, then
push to GitHub — Render will auto-redeploy.

---

## Summary of Live URLs

| Service | URL |
|---------|-----|
| GitHub repo | `https://github.com/<YOUR_USERNAME>/syntera` |
| Backend API | `https://syntera-backend.onrender.com` |
| API docs | `https://syntera-backend.onrender.com/api/docs` |
| Frontend | `https://syntera.vercel.app` |

---

## Environment Variables Reference

See `.env.example` for the full list. Minimum required for production:

```
LLM_API_KEY=sk-...          # OpenAI key
EMBEDDING_PROVIDER=openai   # or "hash" for free/no-key mode
```
