#!/usr/bin/env python
"""
CodeDoc AI - Command Line Interface
"""
import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from pathlib import Path

from config import get_settings
from orchestrator import get_orchestrator, Task, TaskType
from agents.qa_agent import QAAgent

console = Console()
settings = get_settings()


@click.group()
def cli():
    """CodeDoc AI - Autonomous Codebase Documenter"""
    pass


@cli.command()
@click.option('--repo', required=True, help='Repository URL or local path')
@click.option('--branch', default='main', help='Branch to index')
@click.option('--quiet', is_flag=True, help='Suppress progress output')
def ingest(repo: str, branch: str, quiet: bool):
    """Ingest and index a repository"""
    console.print(f"\n[bold blue]Indexing repository:[/bold blue] {repo}")
    
    async def run_ingest():
        orchestrator = get_orchestrator()
        
        task = Task(
            task_id=f"ingest-{hash(repo)}",
            task_type=TaskType.REPO_INGEST,
            payload={
                "repo_url": repo,
                "branch": branch
            }
        )
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console if not quiet else None
        ) as progress:
            progress_task = progress.add_task("Indexing...", total=None)
            
            result = await orchestrator.execute_task(task)
            
            progress.update(progress_task, completed=True)
        
        if result.status.value == "completed":
            console.print(f"\n[green]✓[/green] Repository indexed successfully!")
            console.print(f"   Latency: {result.completed_at - result.started_at:.2f}s")
        else:
            console.print(f"\n[red]✗[/red] Indexing failed: {result.error}")
    
    asyncio.run(run_ingest())


@cli.command()
@click.option('--repo-id', help='Repository ID to search (optional)')
def chat(repo_id: str = None):
    """Interactive chat interface"""
    console.print("\n[bold blue]CodeDoc AI - Chat Mode[/bold blue]")
    console.print("Ask questions about your codebase. Type 'exit' to quit.\n")
    
    qa_agent = QAAgent()
    
    while True:
        try:
            query = console.input("[bold green]You:[/bold green] ")
            
            if query.lower() in ['exit', 'quit', 'q']:
                console.print("\n[yellow]Goodbye![/yellow]")
                break
            
            if not query.strip():
                continue
            
            # Answer question
            with console.status("[bold yellow]Thinking...", spinner="dots"):
                result = qa_agent.answer_question(query, repo_id=repo_id)
            
            # Display answer
            console.print(f"\n[bold cyan]CodeDoc:[/bold cyan] {result.answer}")
            
            if result.sources:
                console.print("\n[dim]Sources:[/dim]")
                for i, source in enumerate(result.sources[:3], 1):
                    console.print(
                        f"  {i}. [dim]{source.file_path}:{source.line_start}-{source.line_end}[/dim]"
                    )
            
            console.print(
                f"\n[dim]Confidence: {result.confidence:.1%} | "
                f"Latency: {result.latency_ms}ms[/dim]\n"
            )
            
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Error:[/red] {str(e)}\n")


@cli.command()
@click.argument('query')
@click.option('--repo-id', help='Repository ID to search')
@click.option('--json', 'output_json', is_flag=True, help='Output as JSON')
def query(query: str, repo_id: str = None, output_json: bool = False):
    """Answer a single question"""
    qa_agent = QAAgent()
    result = qa_agent.answer_question(query, repo_id=repo_id)
    
    if output_json:
        import json
        output = {
            "answer": result.answer,
            "sources": [
                {
                    "file": s.file_path,
                    "lines": f"{s.line_start}-{s.line_end}",
                    "commit": s.commit_hash
                }
                for s in result.sources
            ],
            "confidence": result.confidence,
            "latency_ms": result.latency_ms
        }
        console.print_json(json.dumps(output, indent=2))
    else:
        console.print(qa_agent.format_answer_with_sources(result))


@cli.command()
@click.option('--type', 'doc_type', 
              type=click.Choice(['onboarding', 'api-reference', 'overview']),
              default='onboarding',
              help='Type of documentation to generate')
@click.option('--repo-id', help='Repository ID')
@click.option('--output', type=click.Path(), help='Output file path')
def generate(doc_type: str, repo_id: str = None, output: str = None):
    """Generate documentation"""
    console.print(f"\n[bold blue]Generating {doc_type} documentation...[/bold blue]")
    
    async def run_generate():
        orchestrator = get_orchestrator()
        
        task = Task(
            task_id=f"generate-{doc_type}-{hash(repo_id or 'default')}",
            task_type=TaskType.GENERATE_DOCS,
            payload={
                "doc_type": doc_type,
                "repo_id": repo_id
            }
        )
        
        with console.status("[bold yellow]Generating...", spinner="dots"):
            result = await orchestrator.execute_task(task)
        
        if result.status.value == "completed":
            content = result.result.get("content", "")
            
            if output:
                Path(output).write_text(content)
                console.print(f"\n[green]✓[/green] Documentation saved to: {output}")
            else:
                console.print(f"\n{content}")
            
            console.print(f"\n[dim]Generated in {result.completed_at - result.started_at:.2f}s[/dim]")
        else:
            console.print(f"\n[red]✗[/red] Generation failed: {result.error}")
    
    asyncio.run(run_generate())


@cli.command()
@click.option('--record', is_flag=True, help='Record audio from microphone')
@click.argument('audio_file', required=False)
def voice(record: bool, audio_file: str = None):
    """Process voice query"""
    if not settings.enable_voice:
        console.print("[yellow]Voice feature is disabled. Enable in settings.[/yellow]")
        return
    
    if record:
        console.print("[yellow]Recording not yet implemented[/yellow]")
        return
    
    if not audio_file:
        console.print("[red]Please provide audio file path or use --record[/red]")
        return
    
    async def run_voice():
        orchestrator = get_orchestrator()
        
        task = Task(
            task_id=f"voice-{hash(audio_file)}",
            task_type=TaskType.VOICE_COMMAND,
            payload={"audio_path": audio_file}
        )
        
        with console.status("[bold yellow]Transcribing...", spinner="dots"):
            result = await orchestrator.execute_task(task)
        
        console.print(f"\n[bold]Transcription:[/bold] {result.result.get('transcription', '')}")
        console.print(f"\n[bold]Response:[/bold] {result.result.get('answer', '')}")
    
    asyncio.run(run_voice())


@cli.command()
def metrics():
    """Display system metrics"""
    orchestrator = get_orchestrator()
    metrics_data = orchestrator.get_metrics()
    
    # Create metrics table
    table = Table(title="CodeDoc AI Metrics", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Tasks", str(metrics_data['total_tasks']))
    table.add_row("Successful Tasks", str(metrics_data['successful_tasks']))
    table.add_row("Failed Tasks", str(metrics_data['failed_tasks']))
    table.add_row("Success Rate", f"{metrics_data['success_rate']:.1%}")
    table.add_row("Avg Latency", f"{metrics_data['avg_latency_ms']:.0f}ms")
    
    console.print(table)
    
    # Groq stats
    from utils.groq_client import get_groq_client
    groq = get_groq_client()
    groq_stats = groq.get_stats()
    
    table2 = Table(title="Groq API Stats", show_header=True)
    table2.add_column("Metric", style="cyan")
    table2.add_column("Value", style="green")
    
    table2.add_row("Total API Calls", str(groq_stats['total_calls']))
    table2.add_row("Avg Latency", f"{groq_stats['avg_latency_ms']:.0f}ms")
    table2.add_row("Total Tokens", f"{groq_stats['total_tokens']:,}")
    table2.add_row("Errors", str(groq_stats['errors']))
    table2.add_row("Error Rate", f"{groq_stats['error_rate']:.1%}")
    
    console.print(table2)


@cli.command()
def status():
    """Check system status"""
    console.print("\n[bold]CodeDoc AI Status[/bold]\n")
    
    # Check services
    checks = [
        ("Groq API", _check_groq),
        ("Vector DB", _check_vectordb),
        ("Redis", _check_redis),
    ]
    
    for name, check_func in checks:
        status_icon = "[green]✓[/green]" if check_func() else "[red]✗[/red]"
        console.print(f"{status_icon} {name}")


def _check_groq() -> bool:
    """Check Groq API connectivity"""
    try:
        from utils.groq_client import get_groq_client
        client = get_groq_client()
        # Simple test
        return client.api_key is not None
    except:
        return False


def _check_vectordb() -> bool:
    """Check vector DB connectivity"""
    try:
        db_path = Path(settings.vector_db_path)
        return db_path.exists() or settings.vector_db_type == "milvus"
    except:
        return False


def _check_redis() -> bool:
    """Check Redis connectivity"""
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        r.ping()
        return True
    except:
        return False


if __name__ == '__main__':
    cli()
