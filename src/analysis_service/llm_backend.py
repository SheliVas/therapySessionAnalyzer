from typing import Dict, Any, List

from src.analysis_service.cache_keys import llm_chunk_cache_key
from src.analysis_service.domain import AnalysisBackend, AnalysisResult
from src.analysis_service.llm_client import LLMClient
from src.analysis_service.redis_cache import RedisCache


class LLMAnalysisBackend(AnalysisBackend):
    """LLM analysis backend with Redis caching and emotion timeline."""
    
    def __init__(
        self,
        llm_client: LLMClient,
        redis_cache: RedisCache,
        cache_ttl_seconds: int = 3600,
        prompt_id: str = "default",
    ):
        """Initialize cached LLM backend.
        
        Args:
            llm_client: The LLM client to use for analysis.
            redis_cache: Redis cache for storing results.
            cache_ttl_seconds: Time to live for cached results in seconds.
            prompt_id: Identifier for the prompt version (used in cache key).
        """
        self.llm_client = llm_client
        self.redis_cache = redis_cache
        self.cache_ttl_seconds = cache_ttl_seconds
        self.prompt_id = prompt_id
    
    def analyze(self, transcript_text: str) -> AnalysisResult:
        """Analyze transcript with caching and emotion timeline.
        
        Args:
            transcript_text: The transcript to analyze.
        
        Returns:
            AnalysisResult with word_count and extra containing backend,
            chunks, and emotion_timeline.
        """
        word_count = len(transcript_text.split())
        chunks = self._split_transcript(transcript_text)
        
        chunk_results = []
        for chunk in chunks:
            cache_key = llm_chunk_cache_key(chunk=chunk, prompt_id=self.prompt_id)
            cached_result = self.redis_cache.get(cache_key)
            
            if cached_result is not None:
                result = cached_result
            else:
                result = self.llm_client.analyze_transcript(chunk)
                self.redis_cache.set(cache_key, result, self.cache_ttl_seconds)
            
            chunk_results.append(result)
        
        emotion_timeline = self._derive_emotion_timeline(chunk_results)
        
        return AnalysisResult(
            video_id="",
            word_count=word_count,
            extra={
                "backend": "llm",
                "chunks": chunk_results,
                "emotion_timeline": emotion_timeline,
            }
        )
    
    def _split_transcript(self, transcript_text: str) -> List[str]:
        """Split transcript into chunks (by paragraphs/empty lines).
        
        Args:
            transcript_text: The transcript to split.
        
        Returns:
            List of non-empty chunks.
        """
        if not transcript_text.strip():
            return []
        
        paragraphs = transcript_text.split('\n\n')
        chunks = [p.strip() for p in paragraphs if p.strip()]
        return chunks
    
    def _derive_emotion_timeline(self, chunk_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Derive emotion timeline from chunk results.
        
        Args:
            chunk_results: List of LLM results per chunk.
        
        Returns:
            List of emotion timeline entries with emotion and chunk_index.
        """
        timeline = []
        for idx, result in enumerate(chunk_results):
            emotion = result.get("emotion", "neutral")
            timeline.append({
                "emotion": emotion,
                "chunk_index": idx,
            })
        return timeline
