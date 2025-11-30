"""
CodeDoc AI - REST API
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import asyncio

from config import get_settings
from orchestrator import get_orchestrator, Task, TaskType
from agents.qa_agent import QAAgent

settings = get_settings()
app = FastAPI(title="CodeDoc AI", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request models
class IngestRequest(BaseModel):
    repo_url: str
    branch: str = "main"


class QueryRequest(BaseModel):
    query: str
    repo_id: Optional[str] = None


class GenerateDocsRequest(BaseModel):
    doc_type: str = "onboarding"
    repo_id: Optional[str] = None


# Routes
@app.get("/")
async def root():
    """API root"""
    return {
        "name": "CodeDoc AI",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}


@app.post("/ingest")
async def ingest_repository(request: IngestRequest):
    """Ingest a repository"""
    orchestrator = get_orchestrator()
    
    task = Task(
        task_id=f"ingest-{hash(request.repo_url)}",
        task_type=TaskType.REPO_INGEST,
        payload={
            "repo_url": request.repo_url,
            "branch": request.branch
        }
    )
    
    result = await orchestrator.execute_task(task)
    
    if result.status.value == "completed":
        return {
            "status": "success",
            "task_id": result.task_id,
            "result": result.result
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@app.post("/query")
async def query_codebase(request: QueryRequest):
    """Ask a question about the codebase"""
    orchestrator = get_orchestrator()
    
    task = Task(
        task_id=f"query-{hash(request.query)}",
        task_type=TaskType.USER_QUERY,
        payload={
            "query": request.query,
            "repo_id": request.repo_id
        }
    )
    
    result = await orchestrator.execute_task(task)
    
    if result.status.value == "completed":
        return {
            "status": "success",
            "answer": result.result.get("answer"),
            "sources": result.result.get("sources"),
            "confidence": result.result.get("confidence"),
            "latency_ms": result.result.get("latency_ms")
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@app.post("/generate")
async def generate_docs(request: GenerateDocsRequest):
    """Generate documentation"""
    orchestrator = get_orchestrator()
    
    task = Task(
        task_id=f"generate-{request.doc_type}",
        task_type=TaskType.GENERATE_DOCS,
        payload={
            "doc_type": request.doc_type,
            "repo_id": request.repo_id
        }
    )
    
    result = await orchestrator.execute_task(task)
    
    if result.status.value == "completed":
        return {
            "status": "success",
            "content": result.result.get("content"),
            "type": request.doc_type
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@app.get("/metrics")
async def get_metrics():
    """Get system metrics"""
    orchestrator = get_orchestrator()
    return orchestrator.get_metrics()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
