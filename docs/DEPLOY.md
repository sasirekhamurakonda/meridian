# Deploy Meridian for $0/month

## Quick checklist (~30 minutes)

1. [ ] [Neon](https://neon.tech) → create project → copy **pooled** URL → change to `postgresql+asyncpg://...`
2. [ ] [Upstash](https://upstash.com) → create Redis → copy **`rediss://`** URL
3. [ ] [Groq](https://console.groq.com) → copy API key (you may already have one)
4. [ ] Push this repo to GitHub
5. [ ] [Render](https://dashboard.render.com) → **New → Blueprint** → connect repo
6. [ ] Set `DATABASE_URL`, `REDIS_URL`, `LLM_API_KEY` when prompted (leave `API_KEY` empty for public UI)
7. [ ] Wait for deploy → open `https://YOUR-APP.onrender.com`
8. [ ] (Optional) [cron-job.org](https://cron-job.org) ping `/health` every 10 min

---

This guide deploys Meridian on entirely free tiers:

| Service | Provider | Cost |
|---------|----------|------|
| API + Worker | [Render](https://render.com) | Free |
| Postgres | [Neon](https://neon.tech) | Free |
| Redis | [Upstash](https://upstash.com) | Free |
| LLM | [Groq](https://console.groq.com) | Free |
| Keepalive | [cron-job.org](https://cron-job.org) | Free |

**Estimated monthly cost: $0**

---

## 1. Create a Neon Postgres Database

1. Sign up at [neon.tech](https://neon.tech)
2. Create a new project (e.g. `meridian`)
3. Copy the **pooled connection string** (important for serverless)
4. Convert the URL format:
   - Neon gives: `postgresql://user:pass@host/db?sslmode=require`
   - You need: `postgresql+asyncpg://user:pass@host/db?ssl=require` (use `ssl=require`, not `sslmode`)

Save as `DATABASE_URL`.

---

## 2. Create an Upstash Redis Instance

1. Sign up at [upstash.com](https://upstash.com)
2. Create a new Redis database (choose a region close to your Render region)
3. Copy the **Redis URL** (use the `rediss://` TLS endpoint)

Save as `REDIS_URL`.

---

## 3. Get a Groq API Key

1. Sign up at [console.groq.com](https://console.groq.com)
2. Create an API key
3. Default model: `llama-3.3-70b-versatile`

Save the key as `LLM_API_KEY`.

---

## 4. Push Code to GitHub

```bash
git init
git add .
git commit -m "Initial Meridian implementation"
git remote add origin https://github.com/YOUR_USER/meridian.git
git push -u origin main
```

---

## 5. Deploy on Render

### Option A: Blueprint (recommended)

1. Go to [dashboard.render.com](https://dashboard.render.com)
2. Click **New → Blueprint**
3. Connect your GitHub repo
4. Render reads `render.yaml` automatically
5. Set the secret env vars when prompted:
   - `DATABASE_URL` — from Neon (step 1)
   - `REDIS_URL` — from Upstash (step 2)
   - `LLM_API_KEY` — from Groq (step 3)

### Option B: Manual

1. **New → Web Service**
2. Connect your repo
3. Runtime: **Docker**
4. Plan: **Free**
5. Health check path: `/health`
6. Add environment variables:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Neon pooled URL (`postgresql+asyncpg://...`) |
| `REDIS_URL` | Upstash TLS URL (`rediss://...`) |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` |
| `LLM_API_KEY` | Your Groq key |
| `LLM_MODEL` | `llama-3.3-70b-versatile` |
| `API_KEY` | Generate a random secret |
| `MAX_CONCURRENT_JOBS` | `2` |
| `RATE_LIMIT_PER_HOUR` | `5` |

7. Click **Create Web Service**

Render builds the Docker image, runs migrations, and starts the API + worker.

---

## 6. Run Database Migrations

Migrations run automatically on each deploy via `scripts/start.sh`.

To run manually:

1. Open the Render **Shell** tab
2. Run: `alembic upgrade head`

---

## 7. Reduce Cold Starts (Optional)

Render free tier spins down after 15 minutes of inactivity. First request after idle may take 30–60 seconds.

**Mitigation:** Set up a free keepalive cron:

1. Sign up at [cron-job.org](https://cron-job.org)
2. Create a job:
   - URL: `https://YOUR_APP.onrender.com/health`
   - Schedule: every 10 minutes
   - Method: GET

---

## 8. Test Your Deployment

```bash
export API_URL=https://meridian-api.onrender.com
export API_KEY=your-api-key

# Submit research
curl -X POST "$API_URL/research" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"query": "What are the latest advances in quantum error correction?"}'

# Stream progress
curl -N -H "X-API-Key: $API_KEY" "$API_URL/research/JOB_ID/stream"

# Get report
curl -H "X-API-Key: $API_KEY" "$API_URL/research/JOB_ID"
```

---

## Free Tier Limits

| Resource | Limit | Mitigation |
|----------|-------|------------|
| Render RAM | 512 MB | fastembed (not sentence-transformers), max 2 concurrent jobs |
| Render idle | 15 min spin-down | cron-job.org keepalive |
| Groq API | Rate-limited | 5 jobs/hour rate limit built in |
| Upstash Redis | 10K commands/day | Event log TTL 24h |
| Neon Postgres | 0.5 GB storage | Sufficient for thousands of reports |

---

## Advanced: Self-Hosted LLM on Oracle Cloud (Optional)

If you want a fully self-hosted stack at $0 with no Groq dependency:

1. Create an [Oracle Cloud Always Free](https://www.oracle.com/cloud/free/) ARM instance (up to 24 GB RAM)
2. Install Docker
3. Run the full `docker-compose.yml` with the `cpu` profile (LocalAI) or `gpu` profile (vLLM)
4. Point `LLM_BASE_URL` to your instance

This requires more ops work but removes external LLM API dependency.

---

## Troubleshooting

### Deploy failed on Render

Open **Render → meridian-api → Logs** and look for the first `ERROR:` line.

| Log message | Fix |
|-------------|-----|
| `DATABASE_URL is not set` | Render → **Environment** → add Neon URL |
| `REDIS_URL is not set` | Add Upstash URL (`rediss://...`) |
| `LLM_API_KEY is not set` | Add Groq API key |
| `Database migration failed` | Fix `DATABASE_URL` format (see below) |
| `Port scan timeout` / health check failed | Do **not** set `PORT` manually — Render assigns it automatically |

**Correct `DATABASE_URL` format (Neon):**
```
postgresql+asyncpg://user:pass@ep-xxx-pooler.region.aws.neon.tech/neondb?ssl=require
```
- Use the **pooled** host (`-pooler` in hostname) from Neon dashboard
- `postgresql+asyncpg://` not `postgresql://`
- `ssl=require` not `sslmode=require`
- URL-encode special characters in the password (`@` → `%40`, `#` → `%23`)

**Correct `REDIS_URL` format (Upstash):**
```
rediss://default:TOKEN@your-db.upstash.io:6379
```
Use `rediss://` (TLS), not `redis://`.

After fixing env vars: **Manual Deploy → Deploy latest commit**.

---

| Problem | Solution |
|---------|----------|
| 503 on first request | Cold start — wait 30–60s or set up keepalive cron |
| `ready` shows `llm: false` | Check `LLM_API_KEY` and `LLM_BASE_URL` |
| `ready` shows `postgres: false` | Ensure URL uses `postgresql+asyncpg://` and `ssl=require` |
| `ready` shows `redis: false` | Use Upstash `rediss://` TLS URL |
| Jobs stuck in `queued` | Worker runs in same container — check Render logs for ARQ errors |
| 429 rate limit | Groq free tier exceeded — wait or reduce `RATE_LIMIT_PER_HOUR` |
