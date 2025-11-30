"""
Groq API client wrapper with error handling, retries, and performance monitoring
"""
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class GroqResponse:
    """Structured response from Groq API"""
    content: str
    model: str
    latency_ms: int
    tokens_used: int
    finish_reason: str


class GroqClientError(Exception):
    """Custom exception for Groq client errors"""
    pass


class GroqClient:
    """
    Wrapper for Groq API with error handling, retries, and monitoring
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.groq_api_key
        self.client = Groq(api_key=self.api_key)
        self.stats = {
            "total_calls": 0,
            "total_latency_ms": 0,
            "total_tokens": 0,
            "errors": 0
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(GroqClientError),
        reraise=True
    )
    def complete(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        json_mode: bool = False
    ) -> GroqResponse:
        """
        Send completion request to Groq API
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Groq model name
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream response
            json_mode: Force JSON output format
            
        Returns:
            GroqResponse object
        """
        start_time = time.time()
        
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            
            response = self.client.chat.completions.create(**kwargs)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Update stats
            self.stats["total_calls"] += 1
            self.stats["total_latency_ms"] += latency_ms
            self.stats["total_tokens"] += response.usage.total_tokens
            
            groq_response = GroqResponse(
                content=response.choices[0].message.content,
                model=response.model,
                latency_ms=latency_ms,
                tokens_used=response.usage.total_tokens,
                finish_reason=response.choices[0].finish_reason
            )
            
            logger.info(
                f"Groq completion: model={model}, latency={latency_ms}ms, "
                f"tokens={response.usage.total_tokens}"
            )
            
            return groq_response
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Groq API error: {str(e)}")
            raise GroqClientError(f"Failed to get completion: {str(e)}")
    
    def embed(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        Generate embeddings for text
        Note: Groq doesn't have direct embedding endpoint yet,
        so we use a workaround or external service
        
        For now, returns mock embeddings. In production, use:
        - sentence-transformers locally
        - or OpenAI embeddings API
        """
        # TODO: Implement actual embedding logic
        # For now, return mock 768-dim vector
        import hashlib
        import struct
        
        # Create deterministic but distributed embeddings from hash
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to 768 floats
        embedding = []
        for i in range(0, 768):
            byte_idx = (i * 4) % len(hash_bytes)
            value = struct.unpack('f', hash_bytes[byte_idx:byte_idx+4] * (4 // len(hash_bytes[byte_idx:byte_idx+4]) + 1)[:4])[0]
            embedding.append(value)
        
        return embedding
    
    def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Transcribe audio file using Whisper on Groq
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Transcribed text
        """
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model=settings.groq_whisper_model,
                    response_format="text"
                )
            
            logger.info(f"Transcribed audio: {len(transcription)} chars")
            return transcription
            
        except Exception as e:
            logger.error(f"Whisper transcription error: {str(e)}")
            raise GroqClientError(f"Failed to transcribe audio: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        avg_latency = (
            self.stats["total_latency_ms"] / self.stats["total_calls"]
            if self.stats["total_calls"] > 0
            else 0
        )
        
        return {
            "total_calls": self.stats["total_calls"],
            "avg_latency_ms": round(avg_latency, 2),
            "total_tokens": self.stats["total_tokens"],
            "errors": self.stats["errors"],
            "error_rate": (
                self.stats["errors"] / self.stats["total_calls"]
                if self.stats["total_calls"] > 0
                else 0
            )
        }
    
    def reset_stats(self):
        """Reset statistics counters"""
        self.stats = {
            "total_calls": 0,
            "total_latency_ms": 0,
            "total_tokens": 0,
            "errors": 0
        }


# Singleton instance
_groq_client: Optional[GroqClient] = None


def get_groq_client() -> GroqClient:
    """Get or create Groq client singleton"""
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client


# Convenience functions for common operations
def quick_complete(prompt: str, model: str, **kwargs) -> str:
    """Quick completion with user prompt"""
    client = get_groq_client()
    messages = [{"role": "user", "content": prompt}]
    response = client.complete(messages, model, **kwargs)
    return response.content


def extract_json(prompt: str, model: str, **kwargs) -> str:
    """Force JSON output"""
    client = get_groq_client()
    messages = [{"role": "user", "content": prompt}]
    response = client.complete(messages, model, json_mode=True, **kwargs)
    return response.content


__all__ = [
    "GroqClient",
    "GroqResponse",
    "GroqClientError",
    "get_groq_client",
    "quick_complete",
    "extract_json"
]
