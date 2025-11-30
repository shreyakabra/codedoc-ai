#!/usr/bin/env python
"""
CodeDoc AI - Quick Demo Script

This script demonstrates the core functionality of CodeDoc AI
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.intake import IntakeAgent
from agents.parser import ParserAgent
from agents.qa_agent import QAAgent
from agents.summarizer import SummarizerAgent


def print_section(title):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


async def main():
    """Run the demo"""
    print_section("CodeDoc AI - Demo")
    
    # 1. Intake Demo
    print_section("1. Repository Ingestion")
    print("Initializing Intake Agent...")
    intake = IntakeAgent()
    
    print("\nNote: For full demo, provide a GitHub repository URL")
    print("Example: python demo.py --repo https://github.com/pallets/flask")
    
    # 2. Parser Demo
    print_section("2. Code Parsing")
    parser = ParserAgent()
    
    sample_code = '''
def calculate_total(items: list) -> float:
    """
    Calculate total price of items.
    
    Args:
        items: List of item prices
        
    Returns:
        Total sum
    """
    return sum(items)
'''
    
    print("Parsing sample Python code...")
    result = parser.parse_file("demo.py", content=sample_code)
    print(f"✓ Found {len(result.get('functions', []))} functions")
    
    # 3. Q&A Demo
    print_section("3. Question Answering")
    qa = QAAgent()
    
    print("Asking: 'How does this code work?'")
    answer_result = qa.answer_question("How does calculate_total work?")
    print(f"\nAnswer: {answer_result.answer}")
    print(f"Confidence: {answer_result.confidence:.1%}")
    print(f"Latency: {answer_result.latency_ms}ms")
    
    # 4. Documentation Demo
    print_section("4. Documentation Generation")
    summarizer = SummarizerAgent()
    
    print("Generating onboarding guide...")
    guide = summarizer.generate_onboarding_guide(
        "Demo Repository",
        context="A simple demonstration repository"
    )
    print(f"\n{guide[:300]}...")
    
    print_section("Demo Complete!")
    print("To run the full system:")
    print("  1. python src/cli.py ingest --repo <github_url>")
    print("  2. python src/cli.py chat")
    print("  3. python src/cli.py generate --type onboarding")
    
    # Cleanup
    intake.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
