"""
Configuration management for CodeDoc AI
"""
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "CodeDoc AI"
    debug: bool = False
    log_level: str = "INFO"
    
    # Groq API
    groq_api_key: str = Field(..., description="Groq API key")
    groq_model_orchestrator: str = "llama-3.3-70b-versatile"
    groq_model_qa: str = "llama-3.3-70b-versatile"
    groq_model_parser: str = "llama-scout"  # Multimodal model
    groq_model_summarizer_short: str = "gemma2-9b-it"
    groq_model_summarizer_long: str = "llama-3.3-70b-versatile"
    groq_model_embeddings: str = "gemma2-9b-it"
    groq_model_intake: str = "gemma2-9b-it"
    groq_model_change: str = "llama-3.3-70b-versatile"
    groq_whisper_model: str = "whisper-large-v3"
    groq_timeout: int = 60
    groq_max_retries: int = 3
    
    # Vector Database
    vector_db_type: str = "faiss"  # faiss or milvus
    vector_db_path: str = "./data/faiss_index"
    vector_db_dimension: int = 768
    metadata_db_url: str = "sqlite:///./data/metadata.db"
    
    # Performance
    max_workers: int = 10
    batch_size: int = 50
    chunk_size: int = 512  # tokens per chunk
    chunk_overlap: int = 50
    similarity_top_k: int = 10
    
    # GitHub MCP
    github_app_id: Optional[str] = None
    github_private_key_path: Optional[str] = None
    github_webhook_secret: Optional[str] = None
    github_token: Optional[str] = None  # Personal access token (for testing)
    
    # Jira MCP
    jira_base_url: Optional[str] = None
    jira_email: Optional[str] = None
    jira_api_token: Optional[str] = None
    jira_project_key: str = "DOC"
    
    # Confluence MCP
    confluence_base_url: Optional[str] = None
    confluence_email: Optional[str] = None
    confluence_api_token: Optional[str] = None
    confluence_space_key: str = "DEV"
    
    # Redis (for task queue)
    redis_url: str = "redis://localhost:6379/0"
    
    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    
    # Agent SLA thresholds
    qa_response_timeout_ms: int = 500  # p50 target
    pr_analysis_timeout_s: int = 2
    ingestion_rate_target: int = 1000  # files per minute
    
    # Error handling
    circuit_breaker_threshold: int = 5  # failures before opening
    circuit_breaker_timeout: int = 60  # seconds
    retry_backoff_base: int = 1  # seconds
    retry_max_attempts: int = 3
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090
    sentry_dsn: Optional[str] = None
    
    # Feature flags
    enable_voice: bool = False
    enable_multimodal: bool = True
    enable_jira_integration: bool = False
    enable_confluence_integration: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Prompt templates
class PromptTemplates:
    """Centralized prompt templates for all agents"""
    
    PARSER_EXTRACT = """You are a code analysis expert. Analyze the following code file and extract structured information.

File: {file_path}
Language: {language}

Code:
```{language}
{code}
```

Extract and return JSON with:
{{
  "functions": [
    {{
      "name": "function_name",
      "signature": "full signature",
      "docstring": "summary (<=20 words)",
      "line_start": int,
      "line_end": int,
      "complexity": "low|medium|high"
    }}
  ],
  "classes": [...similar structure...],
  "imports": ["list", "of", "imports"],
  "todos": ["TODO/FIXME items with line numbers"],
  "public_api": ["exported functions/classes"]
}}

Be precise. Only include items actually present in the code."""

    SUMMARIZER_SHORT = """You are a technical documentation expert. Create a concise summary.

Code chunks:
{chunks}

Produce:
1. One-sentence purpose statement
2. 3 bullet points on key behavior
3. Notable dependencies or risks (if any)

Be concise. Use developer-friendly language. Max 50 words total."""

    SUMMARIZER_ONBOARDING = """You are writing an onboarding guide for new developers joining this codebase.

Codebase context:
{context}

Create a comprehensive onboarding guide covering:
1. **Project Overview**: What this codebase does (2-3 sentences)
2. **Architecture**: High-level structure and key modules
3. **Getting Started**: How to set up locally
4. **Key Concepts**: Important patterns, conventions, or domain knowledge
5. **Common Tasks**: How to add features, run tests, deploy
6. **Resources**: Where to find more info

Write in a friendly, welcoming tone. Use markdown formatting.
Target: 800-1200 words."""

    QA_WITH_RETRIEVAL = """You are a helpful coding assistant answering questions about a codebase.

Retrieved context (ordered by relevance):
{context}

User question: {question}

Instructions:
1. Answer the question clearly and concisely
2. Include minimal code snippets when helpful (< 10 lines)
3. ALWAYS cite sources as "Source: file_path:line_start-line_end"
4. If the context is insufficient, say so and suggest what to search for
5. Provide a confidence score (0.0-1.0) at the end

Answer:"""

    CHANGE_ANALYSIS = """You are analyzing a code change in a pull request.

Diff:
{diff}

Historical context:
{context}

Analyze and return JSON:
{{
  "summary": "Brief description of changes (1-2 sentences)",
  "modified_files": [
    {{
      "path": "file path",
      "change_type": "added|modified|deleted",
      "key_changes": ["list of notable changes"]
    }}
  ],
  "breaking_changes": ["list if any"],
  "risk_flags": [
    {{
      "severity": "low|medium|high",
      "description": "what's risky and why"
    }}
  ],
  "test_coverage_impact": "increased|decreased|unchanged",
  "affected_documentation": ["which docs need updates"]
}}

Be thorough but concise."""

    ORCHESTRATOR_ROUTING = """You are an orchestrator deciding which agents to invoke.

Request type: {request_type}
Request details: {request_details}

Available agents:
- intake: Validate and fetch repositories
- parser: Extract code structure and metadata
- chunker_indexer: Create embeddings and index
- summarizer: Generate documentation
- qa: Answer code questions
- change: Analyze PR changes

Return JSON with agent sequence:
{{
  "agents": ["agent1", "agent2", ...],
  "parallel": [["agent_a", "agent_b"]],  // agents that can run in parallel
  "estimated_time_ms": int
}}

Optimize for speed and correctness."""


# Export
__all__ = ["Settings", "get_settings", "PromptTemplates"]
