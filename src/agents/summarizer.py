"""
Summarizer Agent - Documentation generation at various granularities
"""
import logging
from typing import Dict, Optional

from config import get_settings, PromptTemplates
from utils.groq_client import get_groq_client

logger = logging.getLogger(__name__)
settings = get_settings()


class SummarizerAgent:
    """
    Summarizer Agent - Generate documentation
    
    Responsibilities:
    - Generate function/class summaries
    - Create module overviews
    - Build onboarding guides
    - Produce release notes
    - Generate API reference docs
    """
    
    def __init__(self):
        self.groq = get_groq_client()
        self.model_short = settings.groq_model_summarizer_short
        self.model_long = settings.groq_model_summarizer_long
    
    def generate_short_summary(self, chunks: list) -> str:
        """
        Generate short summary (< 50 words)
        
        Args:
            chunks: List of code chunks to summarize
            
        Returns:
            Short summary text
        """
        logger.info(f"Generating short summary for {len(chunks)} chunks")
        
        chunks_text = "\n\n".join([
            f"[{c.get('metadata', {}).get('file_path', 'unknown')}]\n{c.get('text', '')}"
            for c in chunks[:5]  # Limit to first 5 chunks
        ])
        
        prompt = PromptTemplates.SUMMARIZER_SHORT.format(chunks=chunks_text)
        
        try:
            response = self.groq.complete(
                messages=[{"role": "user", "content": prompt}],
                model=self.model_short,
                temperature=0.3,
                max_tokens=200
            )
            
            return response.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating short summary: {str(e)}")
            return "Error generating summary"
    
    def generate_onboarding_guide(self, repo_url: str, context: Optional[str] = None) -> str:
        """
        Generate comprehensive onboarding guide
        
        Args:
            repo_url: Repository URL
            context: Optional additional context
            
        Returns:
            Markdown onboarding guide
        """
        logger.info(f"Generating onboarding guide for {repo_url}")
        
        # Use long-form model for detailed guide
        if context is None:
            context = f"Repository: {repo_url}\n\nGenerate a comprehensive onboarding guide."
        
        prompt = PromptTemplates.SUMMARIZER_ONBOARDING.format(context=context)
        
        try:
            response = self.groq.complete(
                messages=[{"role": "user", "content": prompt}],
                model=self.model_long,
                temperature=0.5,
                max_tokens=2048
            )
            
            guide = response.content.strip()
            logger.info(f"Generated onboarding guide: {len(guide)} characters")
            return guide
            
        except Exception as e:
            logger.error(f"Error generating onboarding guide: {str(e)}")
            return f"# Onboarding Guide\n\nError: {str(e)}"
    
    def generate_api_reference(self, parsed_files: list) -> str:
        """
        Generate API reference documentation
        
        Args:
            parsed_files: List of parsed file structures
            
        Returns:
            Markdown API reference
        """
        logger.info(f"Generating API reference for {len(parsed_files)} files")
        
        # Build API reference structure
        sections = ["# API Reference\n"]
        
        for file_data in parsed_files[:10]:  # Limit for demo
            file_path = file_data.get("file_path", "unknown")
            sections.append(f"\n## {file_path}\n")
            
            # Add functions
            for func in file_data.get("functions", []):
                name = func.get("name", "unknown")
                sig = func.get("signature", "")
                doc = func.get("docstring", "No description")
                
                sections.append(f"\n### `{name}`\n")
                sections.append(f"```python\n{sig}\n```\n")
                sections.append(f"{doc}\n")
        
        return "\n".join(sections)
    
    def generate_overview(self, repo_url: str) -> Dict:
        """
        Generate module-level overview
        
        Args:
            repo_url: Repository URL
            
        Returns:
            Dict with overview content
        """
        logger.info(f"Generating overview for {repo_url}")
        
        return {
            "repo_url": repo_url,
            "overview": f"Repository overview for {repo_url}",
            "modules": [],
            "key_features": []
        }
    
    def generate_docs(self, doc_type: str, repo_id: Optional[str] = None) -> Dict:
        """
        Generate documentation of specified type
        
        Args:
            doc_type: Type of documentation (onboarding, api-reference, overview)
            repo_id: Repository identifier
            
        Returns:
            Dict with generated documentation
        """
        logger.info(f"Generating {doc_type} documentation")
        
        if doc_type == "onboarding":
            content = self.generate_onboarding_guide(
                repo_url=repo_id or "unknown",
                context="Generate comprehensive onboarding documentation"
            )
        elif doc_type == "api-reference":
            content = self.generate_api_reference([])
        elif doc_type == "overview":
            result = self.generate_overview(repo_id or "unknown")
            content = result.get("overview", "")
        else:
            content = f"Unknown documentation type: {doc_type}"
        
        return {
            "type": doc_type,
            "content": content,
            "repo_id": repo_id
        }


# Example usage
if __name__ == "__main__":
    agent = SummarizerAgent()
    
    # Test short summary
    chunks = [
        {
            "text": "def hello_world(name): return f'Hello, {name}!'",
            "metadata": {"file_path": "test.py"}
        }
    ]
    
    summary = agent.generate_short_summary(chunks)
    print(f"Short summary: {summary}")
    
    # Test onboarding guide
    guide = agent.generate_onboarding_guide("https://github.com/example/repo")
    print(f"\nOnboarding guide:\n{guide[:500]}...")
