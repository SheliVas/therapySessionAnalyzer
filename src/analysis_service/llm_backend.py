from typing import Dict, Any, List, Callable, Optional
import json
import logging
import time

from src.analysis_service.cache_keys import utterance_tagging_cache_key
from src.analysis_service.cached_operation import execute_cached_operation
from src.analysis_service.domain import AnalysisBackend, AnalysisResult
from src.analysis_service.llm_client import LLMClient
from src.analysis_service.redis_cache import RedisCache
from src.analysis_service.speaker_role_mapper import map_speakers_to_roles
from src.analysis_service.llm_prompts import UTTERANCE_TAGGING_PROMPT_TEMPLATE, UTTERANCES_PLACEHOLDER
from src.analysis_service.transcript_parser import parse_transcript
from src.analysis_service.llm_output_validators import validate_utterance_tagging_output
from src.analysis_service.recommendations import generate_therapist_recommendations

logger = logging.getLogger(__name__)


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
    
    def analyze(
        self, 
        transcript_text: str, 
        video_id: str,
        on_progress: Optional[Callable[[AnalysisResult], None]] = None
    ) -> AnalysisResult:
        """Analyze transcript with per-utterance tagging.
        
        Args:
            transcript_text: The transcript to analyze.
            video_id: The ID of the video being analyzed.
            on_progress: Optional callback to report partial results.
        
        Returns:
            AnalysisResult with word_count and analysis containing tagging and recommendations.
        """
        started_at = time.perf_counter()
        logger.info("llm_backend.analyze.start video_id=%s", video_id)
        word_count = len(transcript_text.split())
        utterances = parse_transcript(transcript_text)
        logger.info(
            "llm_backend.parsed video_id=%s utterances=%d word_count=%d",
            video_id,
            len(utterances),
            word_count,
        )
        
        if not utterances:
            logger.info("llm_backend.no_utterances video_id=%s", video_id)
            return AnalysisResult(
                video_id=video_id,
                word_count=word_count,
                analysis={
                    "tagging": {"utterances": []},
                    "recommendations": {"therapist_recommendations": []}
                }
            )

        # 1. Role Mapping
        role_mapping_result = map_speakers_to_roles(
            utterances=utterances,
            llm_client=self.llm_client,
            cache=self.redis_cache,
            prompt_id="speaker-role-mapping-v1", # Standard prompt ID for mapping
            ttl_seconds=self.cache_ttl_seconds
        )
        logger.info("llm_backend.speaker_roles.mapped video_id=%s", video_id)
        speaker_roles = role_mapping_result["speaker_roles"]

        for utt in utterances:
            label = utt["speaker_label"]
            utt["role"] = speaker_roles.get(label, {}).get("role", "unknown")

        # Report Progress: Roles Mapped
        if on_progress:
            try:
                on_progress(AnalysisResult(
                    video_id=video_id,
                    word_count=word_count,
                    analysis={
                        "tagging": {"utterances": utterances},
                        "recommendations": {"therapist_recommendations": []}
                    }
                ))
            except Exception as e:
                logger.error("Failed to report progress (Roles Mapped): %s", e)

        # 2. Tagging
        tagged_utterances = self._tag_utterances(utterances)
        logger.info("llm_backend.utterances.tagged video_id=%s", video_id)
        
        # Report Progress: Tagged
        if on_progress:
            try:
                on_progress(AnalysisResult(
                    video_id=video_id,
                    word_count=word_count,
                    analysis={
                        "tagging": {"utterances": tagged_utterances},
                        "recommendations": {"therapist_recommendations": []}
                    }
                ))
            except Exception as e:
                logger.error("Failed to report progress (Tagged): %s", e)

        # 3. Recommendations
        recommendations = generate_therapist_recommendations(
            video_id=video_id,
            utterances=tagged_utterances,
            llm_client=self.llm_client,
            cache=self.redis_cache,
            prompt_id=self.prompt_id,
            ttl_seconds=self.cache_ttl_seconds,
        )
        logger.info(
            "llm_backend.recommendations.generated video_id=%s count=%d",
            video_id,
            len(recommendations.get("therapist_recommendations", [])),
        )
        
        duration = time.perf_counter() - started_at
        logger.info("llm_backend.analyze.completed video_id=%s duration=%.2fs", video_id, duration)
        
        return AnalysisResult(
            video_id=video_id,
            word_count=word_count,
            analysis={
                "tagging": {
                    "utterances": tagged_utterances,
                },
                "recommendations": recommendations,
            }
        )

    def _tag_utterances(self, utterances: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Tag utterances with topic and emotion using LLM and caching."""
        cache_key = utterance_tagging_cache_key(utterances=utterances, prompt_id=self.prompt_id)
        logger.info(
            "llm_backend.tagging.start prompt_id=%s utterances=%d cache_key=%s",
            self.prompt_id,
            len(utterances),
            cache_key,
        )
        
        def _call_llm() -> Any:
            # Create a stable hash of the input utterances for caching
            utterances_json = json.dumps(utterances, sort_keys=True)
            prompt = UTTERANCE_TAGGING_PROMPT_TEMPLATE.replace(UTTERANCES_PLACEHOLDER, utterances_json)
            return self.llm_client.analyze_transcript({"user": prompt})

        def _validate(result: Any) -> Dict[str, Any]:
            return validate_utterance_tagging_output(result)

        validated_result = execute_cached_operation(
            cache=self.redis_cache,
            cache_key=cache_key,
            ttl_seconds=self.cache_ttl_seconds,
            operation=_call_llm,
            validator=_validate,
        )
        logger.info("llm_backend.tagging.completed prompt_id=%s", self.prompt_id)
        
        tagged_list = validated_result["utterances"]
        return self._merge_tags(utterances, tagged_list)

    def _merge_tags(self, utterances: List[Dict[str, Any]], tags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge tags into utterances."""
        for utt, tag in zip(utterances, tags):
            utt["topic"] = tag.get("topic", "other")
            utt["emotion"] = tag.get("emotion", "neutral")
        return utterances
