# System Architecture

## Overview Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           INGEST LAYER                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  MCP Connectors:                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ GitHub   │  │  Jira    │  │Confluence│  │  Local   │               │
│  │ Repos    │  │  API     │  │   API    │  │  Files   │               │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘               │
│       │             │              │             │                      │
│  ┌────▼─────────────▼──────────────▼─────────────▼─────┐               │
│  │        File Upload Handler & Webhook Listener        │               │
│  └──────────────────────┬───────────────────────────────┘               │
└─────────────────────────┼───────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        PREPROCESSING LAYER                               │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐           │
│  │ Language-      │  │  AST           │  │  Multimodal    │           │
│  │ Specific       │  │  Extraction    │  │  Parser        │           │
│  │ Parsers        │  │  (tree-sitter) │  │  (Images/Diag) │           │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘           │
│          │                   │                    │                     │
│          └───────────────────┼────────────────────┘                     │
│                              ▼                                          │
│                 ┌────────────────────────┐                              │
│                 │   Chunking & Metadata  │                              │
│                 │   (file, line, commit) │                              │
│                 └───────────┬────────────┘                              │
│                             │                                           │
│                             ▼                                           │
│                 ┌────────────────────────┐                              │
│                 │  Embedding Service     │                              │
│                 │  (Gemma2)              │                              │
│                 └───────────┬────────────┘                              │
└─────────────────────────────┼───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         STORAGE LAYER                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────┐             │
│  │            Vector Database (FAISS/Milvus)              │             │
│  │  - Code chunks with embeddings                         │             │
│  │  - Metadata: repo, path, commit, function names        │             │
│  │  - Similarity search & re-ranking                      │             │
│  └────────────────────────┬───────────────────────────────┘             │
└─────────────────────────────┼───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          AGENT LAYER (Groq)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                   ORCHESTRATOR AGENT                              │  │
│  │                   (Llama 3.3 70B)                                 │  │
│  │  - Task routing & coordination                                   │  │
│  │  - Error handling & retries                                      │  │
│  │  - SLA enforcement                                               │  │
│  └────┬─────────┬─────────┬─────────┬─────────┬──────────────┬─────┘  │
│       │         │         │         │         │              │         │
│  ┌────▼────┐┌──▼────┐┌───▼───┐┌────▼────┐┌───▼────┐  ┌─────▼─────┐  │
│  │ Intake  ││Parser ││Chunker││Summari- ││   QA   │  │  Change   │  │
│  │ Agent   ││Agent  ││Indexer││  zer    ││ Agent  │  │  Agent    │  │
│  │         ││       ││       ││ Agent   ││        │  │           │  │
│  │(Gemma2) ││(Llama ││(rule- ││(Gemma2/ ││(Llama  │  │ (Llama    │  │
│  │         ││4-Scout││based) ││Llama3.3)││3.3 70B)│  │  3.3 70B) │  │
│  └─────────┘└───────┘└───────┘└─────────┘└────────┘  └───────────┘  │
│       │         │         │         │         │              │         │
│  Voice/File  Multimodal  Vector   Docs     Cited         PR          │
│   Upload     Analysis    Store   Generation Answers     Impact        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        SERVING LAYER                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐           │
│  │  Chat UI  │  │  REST     │  │  Webhook  │  │  Voice    │           │
│  │  (Web)    │  │  API      │  │  Handler  │  │  Interface│           │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘           │
│        └───────────────┴──────────────┴──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     MCP ACTIONS LAYER                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ Create   │  │ Post to  │  │ Open     │  │  Create  │               │
│  │ GitHub   │  │Confluence│  │ Jira     │  │  PR      │               │
│  │ PR       │  │  Pages   │  │ Tickets  │  │ Comments │               │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘               │
└─────────────────────────────────────────────────────────────────────────┘
```

## Agent Roles and Coordination

### 1. Intake Agent
**Model**: Gemma2 (lightweight, fast classification)

**Responsibilities**:
- Validate incoming requests (repo URLs, file uploads, voice commands)
- Authenticate with external services via MCP
- Queue files for processing
- Handle webhook events from GitHub/GitLab

**Inputs**:
- Repo URL, branch name, PR number
- Zip file uploads
- Voice commands (via Whisper transcription)

**Outputs**:
- Validated file list with metadata
- Processing queue entries

**Coordination**:
- Reports to Orchestrator when ingestion complete
- Triggers Parser Agent for each file batch

---

### 2. Parser Agent
**Model**: Llama-4-Scout (multimodal - text + vision)

**Responsibilities**:
- Extract AST from code files (functions, classes, imports)
- Parse docstrings and comments
- Identify TODOs, FIXMEs, and code smells
- Extract diagrams from images (architecture diagrams, flowcharts)
- Determine module dependencies

**Inputs**:
- Source code files (Python, JS, Java, C++, etc.)
- Image files (PNG, JPG of architecture diagrams)
- Markdown documentation

**Outputs**:
```json
{
  "file_path": "src/api/payments.py",
  "language": "python",
  "functions": [
    {
      "name": "process_payment",
      "signature": "process_payment(amount: float, user_id: str) -> PaymentResult",
      "docstring": "Process a payment with retry logic",
      "line_start": 45,
      "line_end": 78
    }
  ],
  "classes": [...],
  "todos": ["TODO: Add idempotency key support"],
  "imports": ["stripe", "redis"],
  "public_api": ["process_payment", "refund_payment"]
}
```

**Coordination**:
- Sends parsed output to Chunker/Indexer
- Alerts Orchestrator on parsing errors

---

### 3. Chunker & Indexer
**Model**: Rule-based + Gemma2 embeddings

**Responsibilities**:
- Split code into semantic chunks (functions, classes, modules)
- Generate metadata (file path, commit hash, timestamps)
- Create embeddings for each chunk
- Upsert to vector database
- Track chunk versions across commits

**Inputs**:
- Parsed code structure from Parser Agent
- Git commit metadata

**Outputs**:
- Vector database entries with metadata
- Chunk index mapping

**Coordination**:
- Confirms indexing completion to Orchestrator
- Provides search interface to QA Agent

---

### 4. Summarizer Agent
**Models**: 
- Gemma2 (short summaries, < 50 words)
- Llama 3.3 70B (long-form guides, release notes)

**Responsibilities**:
- Generate function/class one-liners
- Create module-level overviews
- Build onboarding guides for new developers
- Produce release notes from commit diffs
- Generate API reference documentation

**Inputs**:
- Parsed code chunks with metadata
- Retrieved context from vector DB
- User-specified granularity (function/module/repo)

**Outputs**:
- Markdown documentation at various levels
- Structured summaries in JSON

**Prompt Template** (short summary):
```
You are a technical documentation expert. Given code chunks:
{chunks}

Produce:
1. One-sentence purpose statement
2. 3 bullet points on key behavior
3. Notable dependencies or risks

Be concise. Use developer-friendly language.
```

**Coordination**:
- Called by Orchestrator on-demand or after ingestion
- Can trigger MCP actions to post to Confluence

---

### 5. QA Agent
**Model**: Llama 3.3 70B (reasoning + citation)

**Responsibilities**:
- Answer developer questions about the codebase
- Retrieve relevant code chunks via similarity search
- Provide cited answers with file:line references
- Maintain conversation context for follow-ups
- Flag low-confidence answers for human review

**Inputs**:
- User query (text or voice)
- Conversation history (for context)

**Outputs**:
```json
{
  "answer": "The payment retry logic uses exponential backoff...",
  "sources": [
    {"file": "src/api/payments.py", "lines": "67-72", "commit": "abc123"},
    {"file": "src/utils/retry.py", "lines": "12-25", "commit": "def456"}
  ],
  "confidence": 0.92
}
```

**Prompt Template**:
```
Context: 
{retrieved_chunks with file:line metadata}

Question: {user_question}

Instructions:
1. Answer concisely using the provided context
2. Include minimal code snippets when helpful
3. ALWAYS cite sources as "Source: file_path:line_start-line_end"
4. If context is insufficient, say so and suggest searching specific files
5. Provide confidence score (0-1)
```

**Coordination**:
- Queries Chunker/Indexer for relevant context
- Reports low confidence answers to Orchestrator
- Orchestrator may create Jira ticket for doc improvement

---

### 6. Change Agent
**Model**: Llama 3.3 70B

**Responsibilities**:
- Monitor GitHub webhooks for new commits/PRs
- Generate diff summaries
- Identify breaking changes, deleted tests, API modifications
- Flag high-risk changes (security, performance)
- Auto-update documentation when code changes

**Inputs**:
- Git diffs from commits/PRs
- Historical context from vector DB

**Outputs**:
- Change summary with impact analysis
- Risk flags (breaking changes, test deletions)
- Updated documentation chunks

**Example Output**:
```markdown
## PR #234 Change Summary

**Modified**: `src/api/payments.py`
- Added idempotency key support to `process_payment()` (line 52)
- Breaking change: `amount` parameter now requires Decimal type (was float)

**Risk Flags**:
- ⚠️ Test coverage decreased from 87% → 82%
- ⚠️ Network timeout increased from 5s → 30s

**Affected Documentation**:
- API Reference (payments module)
- Onboarding Guide (payment examples need update)
```

**Coordination**:
- Triggered by Orchestrator on webhook events
- Posts PR comments via MCP GitHub connector
- Creates Jira tickets for doc updates

---

### 7. Orchestrator Agent
**Model**: Llama 3.3 70B (reasoning + decision making)

**Responsibilities**:
- Route tasks to appropriate agents
- Manage agent communication and state
- Implement retry logic with exponential backoff
- Enforce SLA (e.g., QA response < 500ms)
- Handle errors and fallbacks
- Coordinate MCP actions
- Log all operations for debugging

**Decision Logic Example**:
```python
def route_request(request):
    if request.type == "REPO_INGEST":
        return [IntakeAgent, ParserAgent, ChunkerIndexer, SummarizerAgent]
    elif request.type == "USER_QUERY":
        return [QAAgent]  # with retrieval
    elif request.type == "PR_WEBHOOK":
        return [ChangeAgent, SummarizerAgent]
    elif request.type == "GENERATE_DOCS":
        return [SummarizerAgent]
```

**Error Handling**:
- Retries: 3 attempts with exponential backoff (1s, 2s, 4s)
- Circuit breaker: If agent fails 5x in 1 min, disable temporarily
- Fallback: If Llama 3.3 70B fails, use Gemma2 for basic summaries
- Alerting: Notify on critical failures (ingestion blocked, DB unreachable)

**Coordination**:
- Central hub for all agent communication
- Maintains task queue and priorities
- Publishes metrics (latency, throughput, errors)

---

## Model Choices (Groq)

| Use Case | Model | Rationale |
|----------|-------|-----------|
| Voice Input | Whisper (Large v3) | Industry-standard ASR, Groq accelerated |
| Command Parsing | Gemma2 9B | Fast classification, low cost |
| Embeddings | Gemma2 9B | Optimized for semantic similarity |
| Code Parsing | Llama-4-Scout | Multimodal (code + diagrams), strong reasoning |
| Short Summaries | Gemma2 9B | Fast, concise, cost-effective |
| Long-form Docs | Llama 3.3 70B | High-quality narrative generation |
| QA & Citation | Llama 3.3 70B | Strong reasoning, reliable citation |
| Orchestration | Llama 3.3 70B | Complex decision-making, error recovery |

**Groq Advantage**: All models run with **sub-100ms latency** on Groq infrastructure, enabling real-time interactions impossible with traditional LLM APIs.

---

## MCP Integration Points

### 1. GitHub Connector
**Capabilities**:
- Fetch repositories, branches, commits, PRs
- Post PR comments
- Create documentation PRs
- Listen to webhooks (push, PR open/update)
- Add labels to issues/PRs

**Configuration**:
```yaml
github:
  app_id: ${GITHUB_APP_ID}
  private_key: ${GITHUB_PRIVATE_KEY}
  webhook_secret: ${GITHUB_WEBHOOK_SECRET}
  repos:
    - owner/repo-name
```

**MCP Actions**:
- `github.fetch_repo(owner, repo, branch)`
- `github.create_pr(owner, repo, title, body, head, base)`
- `github.post_comment(pr_number, comment_body)`

---

### 2. Jira Connector
**Capabilities**:
- Create tickets for doc gaps
- Link tickets to PRs
- Update ticket status
- Query existing issues

**Configuration**:
```yaml
jira:
  base_url: https://your-domain.atlassian.net
  email: ${JIRA_EMAIL}
  api_token: ${JIRA_API_TOKEN}
  project_key: DOC
```

**MCP Actions**:
- `jira.create_issue(project, summary, description, type)`
- `jira.add_comment(issue_key, comment)`

---

### 3. Confluence Connector
**Capabilities**:
- Create/update pages
- Organize documentation spaces
- Search existing content

**Configuration**:
```yaml
confluence:
  base_url: https://your-domain.atlassian.net/wiki
  email: ${CONFLUENCE_EMAIL}
  api_token: ${CONFLUENCE_API_TOKEN}
  space_key: DEV
```

**MCP Actions**:
- `confluence.create_page(space, title, content)`
- `confluence.update_page(page_id, content)`

---

### 4. Vector DB Connector
**Capabilities**:
- Insert/update embeddings
- Similarity search
- Delete stale chunks
- Backup and restore

**Configuration**:
```yaml
vectordb:
  type: faiss  # or milvus
  dimension: 768
  index_path: /data/faiss_index
  metadata_db: sqlite:///data/metadata.db
```

**MCP Actions**:
- `vectordb.upsert(chunks, embeddings, metadata)`
- `vectordb.search(query_embedding, top_k)`

---

## Data Flow Examples

### Flow A: New Repository Ingestion
```
1. User → Intake Agent: "Index github.com/acme/api-service"
2. Intake Agent → MCP GitHub: Clone repo
3. Intake Agent → Orchestrator: "Repo ready, 247 files"
4. Orchestrator → Parser Agent (parallel): Parse 247 files
5. Parser Agent → Chunker: 1,834 chunks extracted
6. Chunker → Gemma2 Embeddings: Generate vectors
7. Chunker → Vector DB: Upsert 1,834 entries
8. Orchestrator → Summarizer Agent: Generate module docs
9. Summarizer → MCP Confluence: Post onboarding guide
10. Orchestrator → User: "✅ Indexed in 2m 14s. Ask me anything!"
```

### Flow B: Developer Query
```
1. User → QA Agent: "How does retry logic work in payments?"
2. QA Agent → Vector DB: Search("retry logic payments")
3. Vector DB → QA Agent: Top 10 chunks returned
4. QA Agent → Llama 3.3 70B: Compose answer with citations
5. QA Agent → User: Answer + sources (< 500ms total)
```

### Flow C: PR Change Analysis
```
1. GitHub Webhook → Intake Agent: PR #456 opened
2. Intake Agent → Change Agent: Analyze diff
3. Change Agent → Vector DB: Fetch old versions
4. Change Agent → Llama 3.3 70B: Generate impact summary
5. Change Agent → MCP GitHub: Post PR comment
6. Change Agent → MCP Jira: Create "Update API docs" ticket
7. Orchestrator → Summarizer: Re-generate affected docs
```

---

## Performance Targets

| Metric | Target | Groq Advantage |
|--------|--------|----------------|
| QA Response (p50) | < 500ms | 10x faster than OpenAI |
| QA Response (p95) | < 1.5s | Real-time feel |
| Ingestion | 1,000 files/min | Parallel Groq calls |
| PR Analysis | < 2s | Enables auto-posting |
| Summary Generation | < 3s/module | Interactive UX |

---

## Security & Reliability

**Authentication**:
- All MCP connectors use OAuth or API tokens
- Secrets stored in environment variables (never logged)
- Least-privilege access (read-only where possible)

**Error Handling**:
- Circuit breakers for external services
- Exponential backoff (1s → 2s → 4s)
- Graceful degradation (Gemma2 fallback if Llama fails)

**Monitoring**:
- Prometheus metrics exported
- Logging: structured JSON logs
- Alerting: PagerDuty/Slack on critical failures
