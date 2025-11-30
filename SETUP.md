# Setup & Deployment Guide

## Quick Start (5 Minutes)

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- Groq API Key ([get one free](https://console.groq.com))
- Git

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/codedoc-ai.git
cd codedoc-ai

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# 5. Create data directories
mkdir -p data/faiss_index logs

# 6. Start services (Redis, etc.)
docker-compose up -d redis

# 7. Initialize the system
python src/cli.py status
```

### First Run - Index a Repository

```bash
# Index a sample repository
python src/cli.py ingest --repo https://github.com/pallets/flask --branch main

# Ask a question
python src/cli.py query "How does Flask routing work?"

# Interactive chat
python src/cli.py chat
```

---

## Production Deployment

### Option 1: Docker Compose (Recommended)

```bash
# 1. Configure environment
cp .env.example .env
# Fill in production values

# 2. Start all services
docker-compose up -d

# 3. Verify deployment
curl http://localhost:8000/health

# 4. Access services
# API: http://localhost:8000
# UI: http://localhost:8501
# Metrics: http://localhost:9090
# Grafana: http://localhost:3000
```

### Option 2: Kubernetes

```yaml
# See deployment/kubernetes/ for full manifests
# Quick deploy:
kubectl apply -f deployment/kubernetes/
```

### Option 3: Cloud Platforms

#### AWS ECS
```bash
# See deployment/aws/ for Terraform configs
cd deployment/aws
terraform init
terraform apply
```

#### Google Cloud Run
```bash
gcloud run deploy codedoc-ai \
  --image gcr.io/project/codedoc-ai \
  --platform managed \
  --region us-central1
```

---

## Configuration

### Environment Variables

See `.env.example` for full list. Key configurations:

**Required:**
- `GROQ_API_KEY` - Your Groq API key

**Performance Tuning:**
- `MAX_WORKERS=10` - Parallel workers for ingestion
- `BATCH_SIZE=50` - Batch size for processing
- `QA_RESPONSE_TIMEOUT_MS=500` - SLA for Q&A responses

**MCP Integrations:**
- GitHub: `GITHUB_TOKEN` or `GITHUB_APP_ID` + `GITHUB_PRIVATE_KEY_PATH`
- Jira: `JIRA_BASE_URL`, `JIRA_API_TOKEN`
- Confluence: `CONFLUENCE_BASE_URL`, `CONFLUENCE_API_TOKEN`

### Vector Database Options

**FAISS (Default - Local Development)**
```env
VECTOR_DB_TYPE=faiss
VECTOR_DB_PATH=./data/faiss_index
```

**Milvus (Production)**
```env
VECTOR_DB_TYPE=milvus
MILVUS_HOST=milvus.example.com
MILVUS_PORT=19530
```

---

## MCP Configuration

### GitHub Integration

**Option 1: Personal Access Token (Testing)**
1. Go to https://github.com/settings/tokens
2. Create token with `repo` scope
3. Set `GITHUB_TOKEN=your_token`

**Option 2: GitHub App (Production)**
1. Create GitHub App: https://github.com/settings/apps
2. Permissions needed:
   - Repository: Contents (Read), Pull Requests (Read/Write)
   - Webhooks: Active
3. Download private key
4. Configure:
   ```env
   GITHUB_APP_ID=123456
   GITHUB_PRIVATE_KEY_PATH=/path/to/key.pem
   GITHUB_WEBHOOK_SECRET=your_secret
   ```

### Jira Integration

1. Create API token: https://id.atlassian.com/manage/api-tokens
2. Configure:
   ```env
   JIRA_BASE_URL=https://yourcompany.atlassian.net
   JIRA_EMAIL=your-email@company.com
   JIRA_API_TOKEN=your_token
   JIRA_PROJECT_KEY=DOC
   ```

### Confluence Integration

1. Use same API token as Jira
2. Configure:
   ```env
   CONFLUENCE_BASE_URL=https://yourcompany.atlassian.net/wiki
   CONFLUENCE_EMAIL=your-email@company.com
   CONFLUENCE_API_TOKEN=your_token
   CONFLUENCE_SPACE_KEY=DEV
   ```

---

## Scaling & Performance

### Horizontal Scaling

**API Servers:**
```bash
# Scale API instances
docker-compose up -d --scale api=3

# Or in Kubernetes
kubectl scale deployment codedoc-api --replicas=3
```

**Workers:**
```bash
# Scale background workers
docker-compose up -d --scale worker=5
```

### Performance Optimization

**1. Vector DB Optimization**
- Use Milvus for > 1M chunks
- Enable GPU acceleration for embeddings
- Configure index type (IVF_FLAT vs HNSW)

**2. Caching**
- Enable Redis caching for frequent queries
- Cache embeddings for common code patterns

**3. Batch Processing**
```env
MAX_WORKERS=20        # More parallel workers
BATCH_SIZE=100        # Larger batches
```

**4. Groq Optimization**
- Use parallel API calls for ingestion
- Implement request batching
- Monitor rate limits

---

## Monitoring & Observability

### Metrics

Access Prometheus metrics at `http://localhost:9090/metrics`

**Key Metrics:**
- `codedoc_qa_latency_ms` - Q&A response time
- `codedoc_ingestion_rate` - Files processed per minute
- `codedoc_groq_calls_total` - Total Groq API calls
- `codedoc_errors_total` - Error count by type

### Dashboards

Grafana dashboards at `http://localhost:3000`

Default credentials: `admin` / `admin`

**Pre-built Dashboards:**
- System Overview
- Agent Performance
- Groq API Usage
- Error Analysis

### Logging

Logs are written to `./logs/` directory

**Log Levels:**
```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

**Structured Logging:**
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Task completed", extra={"task_id": "123", "latency_ms": 450})
```

### Alerts

Configure alerts in `monitoring/alerts.yml`:

```yaml
groups:
  - name: codedoc
    rules:
      - alert: HighLatency
        expr: codedoc_qa_latency_ms > 1000
        annotations:
          summary: "Q&A latency exceeds 1s"
      
      - alert: HighErrorRate
        expr: rate(codedoc_errors_total[5m]) > 0.1
        annotations:
          summary: "Error rate exceeds 10%"
```

---

## Security Best Practices

### API Keys
- Never commit `.env` to Git
- Use secret management (AWS Secrets Manager, HashiCorp Vault)
- Rotate keys regularly

### Network Security
- Use HTTPS in production
- Implement rate limiting
- Enable CORS only for trusted origins

### Data Privacy
- Repositories are not stored permanently
- Embeddings are anonymous (no raw code in vector DB)
- Audit logs for compliance

### Access Control
```python
# Example: API key authentication
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

@app.get("/query")
async def query(api_key: str = Depends(api_key_header)):
    # Validate API key
    ...
```

---

## Troubleshooting

### Common Issues

**1. "Groq API error: Rate limit exceeded"**
```bash
# Solution: Implement exponential backoff (already included)
# Or upgrade Groq plan
```

**2. "Vector DB connection failed"**
```bash
# Check if FAISS index exists
ls -la data/faiss_index/

# Recreate if needed
rm -rf data/faiss_index
python src/cli.py ingest --repo <repo_url>
```

**3. "Redis connection refused"**
```bash
# Start Redis
docker-compose up -d redis

# Or install locally
brew install redis  # macOS
sudo apt install redis  # Ubuntu
```

**4. "Out of memory during ingestion"**
```bash
# Reduce batch size
export BATCH_SIZE=25

# Or add more RAM to Docker
# Docker Desktop → Settings → Resources → Memory
```

### Debug Mode

```env
DEBUG=true
LOG_LEVEL=DEBUG
```

Then check logs:
```bash
tail -f logs/codedoc.log
```

---

## Backup & Restore

### Backup Vector DB

```bash
# FAISS
tar -czf backup-$(date +%Y%m%d).tar.gz data/faiss_index/

# Milvus
milvus-backup create --collection codedoc
```

### Restore

```bash
# FAISS
tar -xzf backup-20250101.tar.gz

# Milvus
milvus-backup restore --collection codedoc
```

---

## Upgrading

### Update Dependencies

```bash
pip install --upgrade -r requirements.txt
```

### Database Migrations

```bash
# If using PostgreSQL for metadata
alembic upgrade head
```

### Zero-Downtime Deployment

```bash
# Rolling update in Kubernetes
kubectl rollout restart deployment/codedoc-api
kubectl rollout status deployment/codedoc-api
```

---

## Cost Estimation

### Groq API Costs
- Free tier: 14,400 requests/day
- Paid tier: ~$0.27 per 1M tokens
- Estimated cost for 10-dev team: **$5-15/month**

### Infrastructure Costs (AWS Example)
- ECS Fargate (2 vCPU, 4GB): ~$30/month
- RDS PostgreSQL (db.t3.small): ~$30/month
- Milvus on EC2 (t3.medium): ~$40/month
- **Total: ~$100-150/month**

### ROI Calculation
For 10 developers @ $150K/year:
- Time saved: 2-4 hours/week/dev
- Annual value: ~$300K
- **ROI: 2,000%+**

---

## Support & Resources

- **Documentation**: https://docs.codedoc.ai
- **GitHub Issues**: https://github.com/yourusername/codedoc-ai/issues
- **Discord Community**: https://discord.gg/codedoc
- **Email**: support@codedoc.ai

---

## License

MIT License - see LICENSE file for details
