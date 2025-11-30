#!/usr/bin/env python
"""
CodeDoc AI - Main Entry Point
"""
import asyncio
import logging
from config import get_settings
from orchestrator import get_orchestrator
from agents.intake import IntakeAgent
from agents.parser import ParserAgent
from agents.chunker_indexer import ChunkerIndexer
from agents.summarizer import SummarizerAgent
from agents.qa_agent import QAAgent
from agents.change_agent import ChangeAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


def initialize_system():
    """Initialize all agents and register with orchestrator"""
    logger.info("Initializing CodeDoc AI system...")
    
    orchestrator = get_orchestrator()
    
    # Initialize agents
    intake_agent = IntakeAgent()
    parser_agent = ParserAgent()
    chunker_indexer = ChunkerIndexer()
    summarizer_agent = SummarizerAgent()
    qa_agent = QAAgent()
    change_agent = ChangeAgent()
    
    # Register agents with orchestrator
    orchestrator.register_agent("intake", intake_agent)
    orchestrator.register_agent("parser", parser_agent)
    orchestrator.register_agent("chunker_indexer", chunker_indexer)
    orchestrator.register_agent("summarizer", summarizer_agent)
    orchestrator.register_agent("qa", qa_agent)
    orchestrator.register_agent("change", change_agent)
    
    logger.info("All agents registered successfully")
    return orchestrator


async def main():
    """Main application entry point"""
    logger.info(f"Starting {settings.app_name}...")
    
    # Initialize system
    orchestrator = initialize_system()
    
    # Start API server (if running in API mode)
    if settings.api_port:
        logger.info(f"API server would start on {settings.api_host}:{settings.api_port}")
        # Note: Actual server startup is in api.py
    
    logger.info("System ready!")
    logger.info("Use CLI: python src/cli.py")
    logger.info("Or start API: uvicorn src.api:app --reload")


if __name__ == "__main__":
    asyncio.run(main())
