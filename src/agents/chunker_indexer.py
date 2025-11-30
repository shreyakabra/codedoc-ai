"""
Chunker/Indexer - Creates embeddings and manages vector database
"""
import logging
from typing import Dict, List, Optional
import hashlib

from config import get_settings
from utils.groq_client import get_groq_client

logger = logging.getLogger(__name__)
settings = get_settings()


class ChunkerIndexer:
    """
    Chunker/Indexer - Splits code and creates searchable index
    
    Responsibilities:
    - Split code into semantic chunks
    - Generate embeddings
    - Upsert to vector database
    - Provide search interface
    """
    
    def __init__(self, vectordb_connector=None):
        self.groq = get_groq_client()
        self.vectordb = vectordb_connector
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
        
        # In-memory index for demo (replace with real vector DB)
        self.chunks = []
        self.embeddings = []
        
        logger.info("Chunker/Indexer initialized")
    
    def index_chunks(self, parsed_data: Dict) -> Dict:
        """
        Create chunks from parsed data and index them
        
        Args:
            parsed_data: Parsed code structure from Parser Agent
            
        Returns:
            Dict with indexing results
        """
        logger.info(f"Indexing parsed data...")
        
        chunks_created = 0
        
        # Create chunks from functions
        for func in parsed_data.get("functions", []):
            chunk = self._create_chunk(
                text=func.get("signature", "") + "\n" + func.get("docstring", ""),
                metadata={
                    "file_path": parsed_data.get("file_path"),
                    "type": "function",
                    "name": func.get("name"),
                    "line_start": func.get("line_start"),
                    "line_end": func.get("line_end"),
                    "language": parsed_data.get("language")
                }
            )
            self.chunks.append(chunk)
            chunks_created += 1
        
        # Create chunks from classes
        for cls in parsed_data.get("classes", []):
            chunk = self._create_chunk(
                text=f"class {cls.get('name', '')}",
                metadata={
                    "file_path": parsed_data.get("file_path"),
                    "type": "class",
                    "name": cls.get("name"),
                    "line_start": cls.get("line_start", 0),
                    "line_end": cls.get("line_end", 0),
                    "language": parsed_data.get("language")
                }
            )
            self.chunks.append(chunk)
            chunks_created += 1
        
        logger.info(f"Created {chunks_created} chunks")
        
        return {
            "chunks_created": chunks_created,
            "total_chunks": len(self.chunks)
        }
    
    def _create_chunk(self, text: str, metadata: Dict) -> Dict:
        """Create a chunk with metadata"""
        chunk_id = hashlib.md5(
            (text + str(metadata.get("file_path", "")) + str(metadata.get("line_start", ""))).encode()
        ).hexdigest()
        
        return {
            "id": chunk_id,
            "text": text,
            "metadata": metadata,
            "embedding": None  # Will be generated on demand
        }
    
    def search(self, query: str, top_k: int = 10, repo_id: Optional[str] = None) -> List[Dict]:
        """
        Search for relevant chunks
        
        Args:
            query: Search query
            top_k: Number of results to return
            repo_id: Optional repository ID filter
            
        Returns:
            List of relevant chunks with scores
        """
        logger.info(f"Searching for: {query}")
        
        # For demo, return mock results
        # In production, use actual vector similarity search
        
        if not self.chunks:
            logger.warning("No chunks indexed yet")
            return []
        
        # Simple keyword matching for demo
        results = []
        query_lower = query.lower()
        
        for chunk in self.chunks[:top_k]:
            text_lower = chunk["text"].lower()
            
            # Simple scoring based on keyword presence
            score = 0.0
            for word in query_lower.split():
                if word in text_lower:
                    score += 0.3
            
            if score > 0:
                results.append({
                    "text": chunk["text"],
                    "metadata": chunk["metadata"],
                    "score": min(score, 1.0)
                })
        
        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        logger.info(f"Found {len(results)} results")
        return results[:top_k]
    
    def get_chunk_count(self) -> int:
        """Get total number of indexed chunks"""
        return len(self.chunks)
    
    def clear_index(self):
        """Clear all indexed chunks"""
        self.chunks = []
        self.embeddings = []
        logger.info("Index cleared")


# Example usage
if __name__ == "__main__":
    indexer = ChunkerIndexer()
    
    # Test with parsed data
    parsed_data = {
        "file_path": "test.py",
        "language": "python",
        "functions": [
            {
                "name": "hello_world",
                "signature": "def hello_world(name: str) -> str",
                "docstring": "Greet a person by name",
                "line_start": 1,
                "line_end": 10
            }
        ],
        "classes": []
    }
    
    result = indexer.index_chunks(parsed_data)
    print(f"Indexing result: {result}")
    
    # Test search
    results = indexer.search("greet person")
    print(f"Search results: {len(results)}")
