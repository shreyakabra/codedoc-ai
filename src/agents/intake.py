"""
Intake Agent - Repository ingestion and validation
"""
import os
import logging
import tempfile
from typing import Dict, List, Optional
from pathlib import Path
import git

from config import get_settings
from utils.groq_client import get_groq_client

logger = logging.getLogger(__name__)
settings = get_settings()


class IntakeAgent:
    """
    Intake Agent - Handles repository ingestion
    
    Responsibilities:
    - Validate repository URLs
    - Clone repositories
    - Handle file uploads
    - Process voice commands (via Whisper)
    - Queue files for processing
    """
    
    def __init__(self):
        self.groq = get_groq_client()
        self.temp_dir = tempfile.mkdtemp(prefix="codedoc_")
        logger.info(f"Intake Agent initialized. Temp dir: {self.temp_dir}")
    
    def fetch_repo(self, repo_url: str, branch: str = "main") -> Dict:
        """
        Fetch repository from URL
        
        Args:
            repo_url: GitHub repository URL
            branch: Branch to clone
            
        Returns:
            Dict with repository metadata and file list
        """
        logger.info(f"Fetching repository: {repo_url} (branch: {branch})")
        
        try:
            # Create temp directory for this repo
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            repo_path = os.path.join(self.temp_dir, repo_name)
            
            # Clone repository
            logger.info(f"Cloning to {repo_path}...")
            repo = git.Repo.clone_from(repo_url, repo_path, branch=branch)
            
            # Get list of files
            files = []
            for root, dirs, filenames in os.walk(repo_path):
                # Skip .git directory
                if '.git' in root:
                    continue
                    
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, repo_path)
                    
                    # Filter to code files
                    if self._is_code_file(filename):
                        files.append({
                            "path": rel_path,
                            "full_path": file_path,
                            "size": os.path.getsize(file_path),
                            "language": self._detect_language(filename)
                        })
            
            logger.info(f"Repository cloned successfully. Found {len(files)} code files.")
            
            return {
                "repo_url": repo_url,
                "branch": branch,
                "local_path": repo_path,
                "files": files,
                "file_count": len(files),
                "commit_hash": repo.head.commit.hexsha
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch repository: {str(e)}")
            raise
    
    def _is_code_file(self, filename: str) -> bool:
        """Check if file is a code file"""
        code_extensions = {
            '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h',
            '.go', '.rs', '.rb', '.php', '.cs', '.swift', '.kt', '.scala',
            '.md', '.rst', '.txt', '.yaml', '.yml', '.json', '.xml'
        }
        ext = os.path.splitext(filename)[1].lower()
        return ext in code_extensions
    
    def _detect_language(self, filename: str) -> str:
        """Detect programming language from file extension"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.cs': 'csharp',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.md': 'markdown',
            '.rst': 'restructuredtext',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json'
        }
        ext = os.path.splitext(filename)[1].lower()
        return ext_map.get(ext, 'unknown')
    
    def process_voice_command(self, audio_path: str) -> str:
        """
        Process voice command using Whisper
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Transcribed text
        """
        if not settings.enable_voice:
            raise ValueError("Voice feature is disabled")
        
        logger.info(f"Transcribing audio: {audio_path}")
        transcription = self.groq.transcribe_audio(audio_path)
        logger.info(f"Transcription: {transcription}")
        return transcription
    
    def validate_repo_url(self, repo_url: str) -> bool:
        """Validate repository URL format"""
        # Simple validation
        valid_patterns = [
            'github.com',
            'gitlab.com',
            'bitbucket.org'
        ]
        return any(pattern in repo_url for pattern in valid_patterns)
    
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up temp directory: {self.temp_dir}")


# Example usage
if __name__ == "__main__":
    agent = IntakeAgent()
    
    # Test with a public repo
    result = agent.fetch_repo("https://github.com/pallets/flask", "main")
    print(f"Fetched {result['file_count']} files from {result['repo_url']}")
    
    agent.cleanup()
