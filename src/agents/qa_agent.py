"""
QA Agent - Conversational code question answering with citations
"""
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from config import get_settings, PromptTemplates
from utils.groq_client import get_groq_client, GroqResponse

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class CodeSource:
    """Source citation for a code answer"""
    file_path: str
    line_start: int
    line_end: int
    commit_hash: Optional[str] = None
    chunk_text: Optional[str] = None


@dataclass
class QAResult:
    """Result from QA agent"""
    answer: str
    sources: List[CodeSource]
    confidence: float
    latency_ms: int


class QAAgent:
    """
    QA Agent for answering developer questions about codebase
    
    Responsibilities:
    - Embed user queries
    - Retrieve relevant code chunks from vector DB
    - Generate answers using Llama 3.3 70B
    - Provide citations with file:line references
    - Maintain conversation context
    """
    
    def __init__(self, vectordb_connector=None):
        self.groq = get_groq_client()
        self.vectordb = vectordb_connector
        self.conversation_history: List[Dict] = []
        self.model = settings.groq_model_qa
    
    def answer_question(
        self,
        question: str,
        repo_id: Optional[str] = None,
        max_context_chunks: int = 10,
        use_conversation_history: bool = True
    ) -> QAResult:
        """
        Answer a question about the codebase
        
        Args:
            question: User's question
            repo_id: Optional repository ID to filter search
            max_context_chunks: Max number of chunks to retrieve
            use_conversation_history: Include previous Q&A in context
            
        Returns:
            QAResult with answer, sources, and confidence
        """
        import time
        start_time = time.time()
        
        logger.info(f"QA Agent processing question: {question[:100]}...")
        
        # Step 1: Retrieve relevant code chunks
        relevant_chunks = self._retrieve_context(
            question, 
            repo_id=repo_id,
            top_k=max_context_chunks
        )
        
        if not relevant_chunks:
            return QAResult(
                answer="I couldn't find relevant information in the codebase to answer this question. Try rephrasing or asking about specific modules/files.",
                sources=[],
                confidence=0.0,
                latency_ms=int((time.time() - start_time) * 1000)
            )
        
        # Step 2: Format context for LLM
        context_text = self._format_context(relevant_chunks)
        
        # Step 3: Build conversation messages
        messages = self._build_messages(question, context_text, use_conversation_history)
        
        # Step 4: Generate answer
        try:
            response = self.groq.complete(
                messages=messages,
                model=self.model,
                temperature=0.3,  # Lower temperature for factual accuracy
                max_tokens=1024
            )
            
            # Step 5: Parse answer and extract confidence
            answer_text, confidence = self._parse_answer(response.content)
            
            # Step 6: Extract sources from chunks
            sources = self._extract_sources(relevant_chunks)
            
            # Step 7: Update conversation history
            if use_conversation_history:
                self.conversation_history.append({
                    "role": "user",
                    "content": question
                })
                self.conversation_history.append({
                    "role": "assistant",
                    "content": answer_text
                })
                # Keep last 10 messages
                self.conversation_history = self.conversation_history[-10:]
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"QA completed: latency={latency_ms}ms, "
                f"confidence={confidence:.2f}, sources={len(sources)}"
            )
            
            return QAResult(
                answer=answer_text,
                sources=sources,
                confidence=confidence,
                latency_ms=latency_ms
            )
            
        except Exception as e:
            logger.error(f"QA Agent error: {str(e)}")
            return QAResult(
                answer=f"Error generating answer: {str(e)}",
                sources=[],
                confidence=0.0,
                latency_ms=int((time.time() - start_time) * 1000)
            )
    
    def _retrieve_context(
        self,
        query: str,
        repo_id: Optional[str] = None,
        top_k: int = 10
    ) -> List[Dict]:
        """
        Retrieve relevant code chunks from vector DB
        
        Returns:
            List of chunk dicts with metadata
        """
        if not self.vectordb:
            # Mock data for testing
            return [
                {
                    "text": "def process_payment(amount, user_id):\n    # Retry logic with exponential backoff\n    for attempt in range(3):\n        try:\n            return stripe.charge(amount)\n        except Exception:\n            time.sleep(2 ** attempt)",
                    "metadata": {
                        "file_path": "src/api/payments.py",
                        "line_start": 45,
                        "line_end": 52,
                        "commit_hash": "abc123",
                        "function_name": "process_payment"
                    },
                    "score": 0.92
                }
            ]
        
        # Real implementation
        results = self.vectordb.search(
            query=query,
            top_k=top_k,
            repo_id=repo_id
        )
        
        return results
    
    def _format_context(self, chunks: List[Dict]) -> str:
        """Format retrieved chunks for LLM context"""
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            metadata = chunk.get("metadata", {})
            file_path = metadata.get("file_path", "unknown")
            line_start = metadata.get("line_start", 0)
            line_end = metadata.get("line_end", 0)
            
            context_parts.append(
                f"[Chunk {i}] {file_path}:{line_start}-{line_end}\n"
                f"```\n{chunk['text']}\n```\n"
            )
        
        return "\n".join(context_parts)
    
    def _build_messages(
        self,
        question: str,
        context: str,
        use_history: bool
    ) -> List[Dict]:
        """Build message list for LLM"""
        messages = []
        
        # Add conversation history
        if use_history and self.conversation_history:
            messages.extend(self.conversation_history)
        
        # Add current query with context
        prompt = PromptTemplates.QA_WITH_RETRIEVAL.format(
            context=context,
            question=question
        )
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        return messages
    
    def _parse_answer(self, response_text: str) -> Tuple[str, float]:
        """
        Parse answer and extract confidence score
        
        Returns:
            (answer_text, confidence_score)
        """
        # Look for confidence score in response
        confidence = 0.8  # default
        answer = response_text
        
        # Try to extract confidence if present
        if "confidence:" in response_text.lower():
            parts = response_text.split("Confidence:")
            if len(parts) > 1:
                try:
                    confidence = float(parts[1].strip().split()[0])
                    answer = parts[0].strip()
                except:
                    pass
        
        return answer, confidence
    
    def _extract_sources(self, chunks: List[Dict]) -> List[CodeSource]:
        """Extract source citations from chunks"""
        sources = []
        
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            sources.append(CodeSource(
                file_path=metadata.get("file_path", "unknown"),
                line_start=metadata.get("line_start", 0),
                line_end=metadata.get("line_end", 0),
                commit_hash=metadata.get("commit_hash"),
                chunk_text=chunk.get("text", "")[:200]  # First 200 chars
            ))
        
        return sources
    
    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info("Conversation history reset")
    
    def format_answer_with_sources(self, result: QAResult) -> str:
        """
        Format QA result for display with clickable sources
        
        Returns:
            Formatted markdown string
        """
        output = [f"{result.answer}\n"]
        
        if result.sources:
            output.append("\n**Sources:**")
            for i, source in enumerate(result.sources, 1):
                output.append(
                    f"{i}. `{source.file_path}:{source.line_start}-{source.line_end}`"
                )
                if source.commit_hash:
                    output.append(f"   (commit: {source.commit_hash[:7]})")
        
        output.append(f"\n*Confidence: {result.confidence:.1%} | Latency: {result.latency_ms}ms*")
        
        return "\n".join(output)


# Example usage
if __name__ == "__main__":
    # Initialize agent
    qa = QAAgent()
    
    # Ask a question
    result = qa.answer_question("How does payment retry logic work?")
    
    # Display formatted answer
    print(qa.format_answer_with_sources(result))
    
    # Follow-up question (uses conversation history)
    result2 = qa.answer_question("What happens if all retries fail?")
    print(qa.format_answer_with_sources(result2))
