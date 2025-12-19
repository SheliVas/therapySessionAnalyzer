from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from src.analysis_service.llm_client import LLMClient
from src.analysis_service.llm_prompts import (
    SPEAKER_ROLE_MAPPING_PROMPT_TEMPLATE,
    UTTERANCES_PLACEHOLDER,
)
from src.analysis_service.redis_cache import RedisCache


def _json_dumps_deterministic(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _make_cache_key(utterances: list[dict[str, Any]], prompt_id: str) -> str:
    payload = {"prompt_id": prompt_id, "utterances": utterances}
    digest = hashlib.sha256(_json_dumps_deterministic(payload).encode("utf-8")).hexdigest()
    return f"speaker_role_mapping:{digest}"


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


def _is_number_0_1(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return 0.0 <= float(value) <= 1.0


def _build_prompt(utterances: list[dict[str, Any]]) -> str:
    # The template expects the raw utterances JSON array.
    # Keep utterance order (chronological) as provided.
    utterances_json = json.dumps(utterances, ensure_ascii=False)
    return SPEAKER_ROLE_MAPPING_PROMPT_TEMPLATE.replace(UTTERANCES_PLACEHOLDER, utterances_json)


def _validate_llm_output(result: Any, speaker_labels: list[str]) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError("LLM output must be a JSON object")

    expected_top_keys = {"speaker_roles", "overall_confidence"}
    if set(result.keys()) != expected_top_keys:
        raise ValueError("LLM output must have exactly: speaker_roles, overall_confidence")

    speaker_roles = result.get("speaker_roles")
    if not isinstance(speaker_roles, dict):
        raise ValueError("speaker_roles must be an object")

    if set(speaker_roles.keys()) != set(speaker_labels):
        raise ValueError("speaker_roles keys must match the input speaker labels")

    roles_assigned: list[str] = []
    for label in speaker_labels:
        entry = speaker_roles.get(label)
        if not isinstance(entry, dict):
            raise ValueError("Each speaker_roles entry must be an object")

        if set(entry.keys()) != {"role", "confidence", "reason"}:
            raise ValueError("Each speaker_roles entry must have exactly: role, confidence, reason")

        role = entry.get("role")
        if role not in {"therapist", "patient"}:
            raise ValueError("role must be therapist or patient")
        roles_assigned.append(role)

        confidence = entry.get("confidence")
        if not _is_number_0_1(confidence):
            raise ValueError("confidence must be a number in [0,1]")

        reason = entry.get("reason")
        if not isinstance(reason, str):
            raise ValueError("reason must be a string")
        if len(reason) > 120:
            raise ValueError("reason must be <= 120 characters")

    if sorted(roles_assigned) != ["patient", "therapist"]:
        raise ValueError("Exactly one therapist and one patient must be assigned")

    overall_confidence = result.get("overall_confidence")
    if not _is_number_0_1(overall_confidence):
        raise ValueError("overall_confidence must be a number in [0,1]")

    return result


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

    cache_key = _make_cache_key(utterances=utterances, prompt_id=prompt_id)
    cached = cache.get(cache_key)
    if cached is not None:
        return _validate_llm_output(cached, speaker_labels=speaker_labels)

    prompt_text = _build_prompt(
        utterances=utterances,
    )
    llm_result = llm_client.analyze_transcript(prompt_text)
    validated = _validate_llm_output(llm_result, speaker_labels=speaker_labels)
    cache.set(cache_key, validated, ttl_seconds)
    return validated
