"""
Parser Agent - Code structure extraction and analysis
"""
import json
import logging
from typing import Dict, List, Optional

from config import get_settings, PromptTemplates
from utils.groq_client import get_groq_client

logger = logging.getLogger(__name__)
settings = get_settings()


class ParserAgent:
    """
    Parser Agent - Extract code structure and metadata
    
    Responsibilities:
    - Extract AST from code files
    - Parse docstrings and comments
    - Identify TODOs, FIXMEs
    - Extract diagrams from images (multimodal)
    - Determine module dependencies
    """
    
    def __init__(self):
        self.groq = get_groq_client()
        self.model = settings.groq_model_parser
    
    def parse_file(self, file_path: str, content: Optional[str] = None) -> Dict:
        """
        Parse a code file and extract structure
        
        Args:
            file_path: Path to the file
            content: File content (if not provided, will read from file_path)
            
        Returns:
            Dict with parsed code structure
        """
        logger.info(f"Parsing file: {file_path}")
        
        # Read file if content not provided
        if content is None:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        
        # Detect language
        language = self._detect_language(file_path)
        
        # Use Groq to extract structure
        prompt = PromptTemplates.PARSER_EXTRACT.format(
            file_path=file_path,
            language=language,
            code=content[:4000]  # Limit to first 4000 chars for demo
        )
        
        try:
            response = self.groq.complete(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.1,
                max_tokens=2048,
                json_mode=True
            )
            
            # Parse JSON response
            result = json.loads(response.content)
            result["file_path"] = file_path
            result["language"] = language
            
            logger.info(
                f"Parsed {file_path}: "
                f"{len(result.get('functions', []))} functions, "
                f"{len(result.get('classes', []))} classes"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {str(e)}")
            # Return minimal structure on error
            return {
                "file_path": file_path,
                "language": language,
                "functions": [],
                "classes": [],
                "imports": [],
                "todos": [],
                "public_api": [],
                "error": str(e)
            }
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        import os
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php'
        }
        ext = os.path.splitext(file_path)[1].lower()
        return ext_map.get(ext, 'unknown')
    
    def parse_image(self, image_path: str) -> Dict:
        """
        Parse image to extract diagrams (multimodal)
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dict with extracted diagram information
        """
        logger.info(f"Parsing image: {image_path}")
        
        # TODO: Implement multimodal parsing with Llama-4-Scout
        # For now, return stub
        return {
            "image_path": image_path,
            "type": "architecture_diagram",
            "components": [],
            "relationships": [],
            "description": "Diagram parsing not yet implemented"
        }
    
    def extract_dependencies(self, parsed_file: Dict) -> List[str]:
        """Extract dependencies from parsed file"""
        return parsed_file.get("imports", [])
    
    def identify_public_api(self, parsed_file: Dict) -> List[str]:
        """Identify public API from parsed file"""
        return parsed_file.get("public_api", [])


# Example usage
if __name__ == "__main__":
    agent = ParserAgent()
    
    # Test with sample Python code
    sample_code = '''
def hello_world(name: str) -> str:
    """
    Greet a person by name.
    
    Args:
        name: Person's name
        
    Returns:
        Greeting message
    """
    return f"Hello, {name}!"

class Calculator:
    """Simple calculator class"""
    
    def add(self, a: int, b: int) -> int:
        """Add two numbers"""
        return a + b
    
    # TODO: Implement subtract method
'''
    
    result = agent.parse_file("test.py", content=sample_code)
    print(json.dumps(result, indent=2))
