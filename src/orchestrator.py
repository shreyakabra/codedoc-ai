"""
Orchestrator Agent - Central coordinator for all agent activities
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from config import get_settings, PromptTemplates
from utils.groq_client import get_groq_client

logger = logging.getLogger(__name__)
settings = get_settings()


class TaskType(Enum):
    """Types of tasks the orchestrator can handle"""
    REPO_INGEST = "repo_ingest"
    USER_QUERY = "user_query"
    PR_WEBHOOK = "pr_webhook"
    GENERATE_DOCS = "generate_docs"
    VOICE_COMMAND = "voice_command"


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class Task:
    """Represents a task for the orchestrator"""
    task_id: str
    task_type: TaskType
    payload: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class AgentExecution:
    """Tracks individual agent execution"""
    agent_name: str
    started_at: float
    completed_at: Optional[float] = None
    status: TaskStatus = TaskStatus.RUNNING
    result: Optional[Any] = None
    error: Optional[str] = None


class CircuitBreaker:
    """Circuit breaker for agent calls"""
    
    def __init__(self, threshold: int = 5, timeout: int = 60):
        self.threshold = threshold
        self.timeout = timeout
        self.failures: Dict[str, List[float]] = {}
        self.open_until: Dict[str, float] = {}
    
    def is_open(self, agent_name: str) -> bool:
        """Check if circuit is open for this agent"""
        if agent_name in self.open_until:
            if time.time() < self.open_until[agent_name]:
                return True
            else:
                # Reset after timeout
                del self.open_until[agent_name]
                self.failures[agent_name] = []
        return False
    
    def record_failure(self, agent_name: str):
        """Record a failure for this agent"""
        now = time.time()
        if agent_name not in self.failures:
            self.failures[agent_name] = []
        
        # Add failure and remove old ones (> 1 min)
        self.failures[agent_name].append(now)
        self.failures[agent_name] = [
            t for t in self.failures[agent_name] if now - t < 60
        ]
        
        # Check threshold
        if len(self.failures[agent_name]) >= self.threshold:
            self.open_until[agent_name] = now + self.timeout
            logger.warning(
                f"Circuit breaker opened for {agent_name} "
                f"for {self.timeout}s due to {self.threshold} failures"
            )
    
    def record_success(self, agent_name: str):
        """Record a success (resets failure count)"""
        if agent_name in self.failures:
            self.failures[agent_name] = []


class Orchestrator:
    """
    Orchestrator Agent - Coordinates all agent activities
    
    Responsibilities:
    - Route tasks to appropriate agents
    - Manage agent coordination and state
    - Implement retry logic with exponential backoff
    - Enforce SLA (e.g., QA response < 500ms)
    - Handle errors and circuit breaking
    - Coordinate MCP actions
    - Log all operations
    """
    
    def __init__(self):
        self.groq = get_groq_client()
        self.circuit_breaker = CircuitBreaker(
            threshold=settings.circuit_breaker_threshold,
            timeout=settings.circuit_breaker_timeout
        )
        self.tasks: Dict[str, Task] = {}
        self.metrics = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "total_latency_ms": 0
        }
        
        # Agent registry (will be populated as agents are added)
        self.agents: Dict[str, Any] = {}
    
    def register_agent(self, name: str, agent_instance: Any):
        """Register an agent with the orchestrator"""
        self.agents[name] = agent_instance
        logger.info(f"Registered agent: {name}")
    
    async def execute_task(self, task: Task) -> Task:
        """
        Execute a task by routing to appropriate agents
        
        Args:
            task: Task to execute
            
        Returns:
            Updated task with results
        """
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        
        logger.info(f"Executing task {task.task_id}: {task.task_type.value}")
        
        try:
            # Route based on task type
            if task.task_type == TaskType.REPO_INGEST:
                result = await self._handle_repo_ingest(task)
            elif task.task_type == TaskType.USER_QUERY:
                result = await self._handle_user_query(task)
            elif task.task_type == TaskType.PR_WEBHOOK:
                result = await self._handle_pr_webhook(task)
            elif task.task_type == TaskType.GENERATE_DOCS:
                result = await self._handle_generate_docs(task)
            elif task.task_type == TaskType.VOICE_COMMAND:
                result = await self._handle_voice_command(task)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            self.metrics["successful_tasks"] += 1
            
        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {str(e)}")
            task.error = str(e)
            task.status = TaskStatus.FAILED
            self.metrics["failed_tasks"] += 1
            
        finally:
            task.completed_at = time.time()
            latency_ms = int((task.completed_at - task.started_at) * 1000)
            self.metrics["total_latency_ms"] += latency_ms
            self.metrics["total_tasks"] += 1
            
            logger.info(
                f"Task {task.task_id} {task.status.value} "
                f"in {latency_ms}ms"
            )
        
        return task
    
    async def _handle_repo_ingest(self, task: Task) -> Dict:
        """Handle repository ingestion"""
        repo_url = task.payload.get("repo_url")
        branch = task.payload.get("branch", "main")
        
        # Agent sequence: Intake → Parser → Chunker → Summarizer
        results = {}
        
        # Step 1: Intake Agent
        if "intake" in self.agents:
            intake_result = await self._execute_agent(
                "intake",
                "fetch_repo",
                repo_url=repo_url,
                branch=branch
            )
            results["intake"] = intake_result
        
        # Step 2: Parser Agent (can run in parallel on files)
        if "parser" in self.agents and results.get("intake"):
            files = results["intake"].get("files", [])
            parse_tasks = [
                self._execute_agent("parser", "parse_file", file_path=f)
                for f in files[:10]  # Limit for demo
            ]
            parse_results = await asyncio.gather(*parse_tasks, return_exceptions=True)
            results["parser"] = {
                "parsed_files": len([r for r in parse_results if not isinstance(r, Exception)]),
                "errors": len([r for r in parse_results if isinstance(r, Exception)])
            }
        
        # Step 3: Chunker/Indexer
        if "chunker_indexer" in self.agents:
            index_result = await self._execute_agent(
                "chunker_indexer",
                "index_chunks",
                parsed_data=results.get("parser")
            )
            results["indexer"] = index_result
        
        # Step 4: Summarizer (generate initial docs)
        if "summarizer" in self.agents:
            summary_result = await self._execute_agent(
                "summarizer",
                "generate_overview",
                repo_url=repo_url
            )
            results["summarizer"] = summary_result
        
        return {
            "status": "completed",
            "repo_url": repo_url,
            "branch": branch,
            "results": results
        }
    
    async def _handle_user_query(self, task: Task) -> Dict:
        """Handle user query"""
        query = task.payload.get("query")
        repo_id = task.payload.get("repo_id")
        
        # Route to QA Agent
        if "qa" not in self.agents:
            raise ValueError("QA agent not registered")
        
        # Enforce SLA
        start_time = time.time()
        result = await self._execute_agent(
            "qa",
            "answer_question",
            question=query,
            repo_id=repo_id
        )
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Check SLA
        if latency_ms > settings.qa_response_timeout_ms:
            logger.warning(
                f"QA exceeded SLA: {latency_ms}ms > {settings.qa_response_timeout_ms}ms"
            )
        
        return result
    
    async def _handle_pr_webhook(self, task: Task) -> Dict:
        """Handle PR webhook event"""
        pr_number = task.payload.get("pr_number")
        repo_url = task.payload.get("repo_url")
        
        # Route to Change Agent
        if "change" not in self.agents:
            raise ValueError("Change agent not registered")
        
        result = await self._execute_agent(
            "change",
            "analyze_pr",
            pr_number=pr_number,
            repo_url=repo_url
        )
        
        # Post PR comment if configured
        if task.payload.get("auto_comment", True):
            # Use GitHub MCP connector
            pass  # TODO: Implement
        
        return result
    
    async def _handle_generate_docs(self, task: Task) -> Dict:
        """Handle documentation generation"""
        doc_type = task.payload.get("doc_type", "onboarding")
        repo_id = task.payload.get("repo_id")
        
        # Route to Summarizer Agent
        if "summarizer" not in self.agents:
            raise ValueError("Summarizer agent not registered")
        
        result = await self._execute_agent(
            "summarizer",
            "generate_docs",
            doc_type=doc_type,
            repo_id=repo_id
        )
        
        return result
    
    async def _handle_voice_command(self, task: Task) -> Dict:
        """Handle voice command"""
        audio_path = task.payload.get("audio_path")
        
        # Transcribe first
        transcription = self.groq.transcribe_audio(audio_path)
        
        # Route based on transcription
        # Simple intent detection
        if any(word in transcription.lower() for word in ["index", "ingest", "add"]):
            # Repo ingestion
            new_task = Task(
                task_id=f"{task.task_id}-ingest",
                task_type=TaskType.REPO_INGEST,
                payload={"repo_url": "..."}  # Extract from transcription
            )
            return await self.execute_task(new_task)
        else:
            # Treat as query
            new_task = Task(
                task_id=f"{task.task_id}-query",
                task_type=TaskType.USER_QUERY,
                payload={"query": transcription}
            )
            return await self.execute_task(new_task)
    
    async def _execute_agent(
        self,
        agent_name: str,
        method_name: str,
        **kwargs
    ) -> Any:
        """
        Execute an agent method with retries and circuit breaking
        
        Args:
            agent_name: Name of the agent
            method_name: Method to call on agent
            **kwargs: Arguments to pass to method
            
        Returns:
            Agent method result
        """
        # Check circuit breaker
        if self.circuit_breaker.is_open(agent_name):
            raise Exception(f"Circuit breaker open for {agent_name}")
        
        agent = self.agents.get(agent_name)
        if not agent:
            raise ValueError(f"Agent not found: {agent_name}")
        
        method = getattr(agent, method_name, None)
        if not method:
            raise ValueError(f"Method not found: {agent_name}.{method_name}")
        
        # Retry logic
        for attempt in range(settings.retry_max_attempts):
            try:
                # Execute method (could be sync or async)
                if asyncio.iscoroutinefunction(method):
                    result = await method(**kwargs)
                else:
                    result = method(**kwargs)
                
                self.circuit_breaker.record_success(agent_name)
                return result
                
            except Exception as e:
                logger.error(
                    f"Agent {agent_name}.{method_name} failed "
                    f"(attempt {attempt + 1}): {str(e)}"
                )
                
                if attempt < settings.retry_max_attempts - 1:
                    # Exponential backoff
                    wait_time = settings.retry_backoff_base * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                else:
                    # Final failure
                    self.circuit_breaker.record_failure(agent_name)
                    raise
    
    def get_metrics(self) -> Dict:
        """Get orchestrator metrics"""
        avg_latency = (
            self.metrics["total_latency_ms"] / self.metrics["total_tasks"]
            if self.metrics["total_tasks"] > 0
            else 0
        )
        
        return {
            **self.metrics,
            "avg_latency_ms": round(avg_latency, 2),
            "success_rate": (
                self.metrics["successful_tasks"] / self.metrics["total_tasks"]
                if self.metrics["total_tasks"] > 0
                else 0
            )
        }


# Singleton instance
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Get or create orchestrator singleton"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


# Example usage
if __name__ == "__main__":
    async def main():
        orchestrator = get_orchestrator()
        
        # Create a task
        task = Task(
            task_id="task-001",
            task_type=TaskType.REPO_INGEST,
            payload={
                "repo_url": "https://github.com/example/repo",
                "branch": "main"
            }
        )
        
        # Execute task
        result = await orchestrator.execute_task(task)
        print(f"Task completed: {result.status}")
        print(f"Metrics: {orchestrator.get_metrics()}")
    
    asyncio.run(main())
