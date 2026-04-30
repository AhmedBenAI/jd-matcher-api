# Portfolio JD Matcher — Backend

Flask API that uses Claude to analyse job description fit for Ahmed Bendimered's portfolio.

Called by the frontend at [portfolio.vercel.app](https://your-portfolio.vercel.app).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env — add your ANTHROPIC_API_KEY and set FRONTEND_URL to your Vercel domain
python server.py
```

## API

### `POST /api/analyze-jd`
```json
{ "job_description": "..." }
```
Returns a JSON match report with score, verdict, matches, gaps, whyHire, and interviewQs.

### `GET /api/health`
Returns `{ "status": "ok" }`.

## Deployment

**Railway (recommended):**
1. Connect this repo to Railway
2. Set env vars: `ANTHROPIC_API_KEY`, `FRONTEND_URL`, `PORT=5000`
3. Deploy — Railway auto-detects Python

**Render:**
- Build command: `pip install -r requirements.txt`
- Start command: `python server.py`
- Add env vars in dashboard

**After deploying**, update `API_BASE` in the frontend repo's [static/js/app.js](../static/js/app.js) to your backend URL.
