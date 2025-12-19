from __future__ import annotations

import json
from typing import Any, Iterable

from src.analysis_service.cache_keys import speaker_role_mapping_cache_key
from src.analysis_service.llm_client import LLMClient
from src.analysis_service.llm_output_validators import validate_speaker_role_mapping_output
from src.analysis_service.llm_prompts import (
    SPEAKER_ROLE_MAPPING_PROMPT_TEMPLATE,
    UTTERANCES_PLACEHOLDER,
)
from src.analysis_service.redis_cache import RedisCache


def _extract_speaker_labels(utterances: Iterable[dict[str, Any]]) -> list[str]:
    labels: set[str] = set()
    for utterance in utterances:
        label = utterance.get("speaker_label")
        if label is None:
            continue
        if not isinstance(label, str) or not label:
            raise ValueError("speaker_label must be a non-empty string")
        labels.add(label)
    return sorted(labels)


def _build_prompt(utterances: list[dict[str, Any]]) -> str:
    # The template expects the raw utterances JSON array.
    # Keep utterance order (chronological) as provided.
    utterances_json = json.dumps(utterances, ensure_ascii=False)
    return SPEAKER_ROLE_MAPPING_PROMPT_TEMPLATE.replace(UTTERANCES_PLACEHOLDER, utterances_json)


def map_speakers_to_roles(
    utterances: list[dict[str, Any]],
    llm_client: LLMClient,
    cache: RedisCache,
    prompt_id: str,
    ttl_seconds: int,
) -> dict[str, Any]:
    speaker_labels = _extract_speaker_labels(utterances)
    if len(speaker_labels) != 2:
        raise ValueError("Exactly two speakers are required")

    cache_key = speaker_role_mapping_cache_key(utterances=utterances, prompt_id=prompt_id)
    cached = cache.get(cache_key)
    if cached is not None:
        return validate_speaker_role_mapping_output(cached, speaker_labels=speaker_labels)

    prompt_text = _build_prompt(
        utterances=utterances,
    )
    llm_result = llm_client.analyze_transcript(prompt_text)
    validated = validate_speaker_role_mapping_output(llm_result, speaker_labels=speaker_labels)
    cache.set(cache_key, validated, ttl_seconds)
    return validated
