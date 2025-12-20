import json
import logging
from typing import Any, Set, Dict

from src.analysis_service.cache_keys import therapist_recommendations_cache_key
from src.analysis_service.llm_client import LLMClient
from src.analysis_service.redis_cache import RedisCache
from src.analysis_service.cached_operation import execute_cached_operation
from src.analysis_service.llm_output_validators import validate_recommendations_output
from src.analysis_service.llm_prompts import (
    THERAPIST_RECOMMENDATIONS_SYSTEM_PROMPT,
    THERAPIST_RECOMMENDATIONS_USER_PROMPT_TEMPLATE,
    INPUT_JSON_PLACEHOLDER,
)

logger = logging.getLogger(__name__)

def generate_therapist_recommendations(
    video_id: str,
    utterances: list[dict],
    llm_client: LLMClient,
    cache: RedisCache,
    prompt_id: str,
    ttl_seconds: int,
) -> dict:
    """Generate therapist recommendations based on utterances."""
    observed_topics: Set[str] = set()
    observed_emotions: Set[str] = set()
    for u in utterances:
        if "topic" in u and u["topic"]:
            observed_topics.add(u["topic"])
        if "emotion" in u and u["emotion"]:
            observed_emotions.add(u["emotion"])
    logger.info(
        "recommendations.start video_id=%s utterances=%d topics=%d emotions=%d",
        video_id,
        len(utterances),
        len(observed_topics),
        len(observed_emotions),
    )

    cache_key = therapist_recommendations_cache_key(
        video_id=video_id, utterances=utterances, prompt_id=prompt_id
    )

    normalized_utterances = json.dumps(utterances, sort_keys=True)

    def _call_llm() -> Any:
        user_message = THERAPIST_RECOMMENDATIONS_USER_PROMPT_TEMPLATE.replace(
            INPUT_JSON_PLACEHOLDER, normalized_utterances
        )
        
        prompt = {
            "system": THERAPIST_RECOMMENDATIONS_SYSTEM_PROMPT,
            "user": user_message
        }

        return llm_client.analyze_transcript(prompt)

    def _validate(data: Any) -> Dict[str, Any]:
        return validate_recommendations_output(data, valid_topics=observed_topics, valid_emotions=observed_emotions)

    result = execute_cached_operation(
        cache=cache,
        cache_key=cache_key,
        ttl_seconds=ttl_seconds,
        operation=_call_llm,
        validator=_validate,
    )
    logger.info(
        "recommendations.completed video_id=%s recommendations=%d",
        video_id,
        len(result.get("therapist_recommendations", [])),
    )
    return result
