from __future__ import annotations

import hashlib
import json
from typing import Any


def json_dumps_deterministic(value: Any) -> str:
    """Serialize as deterministic JSON string.

    Uses sorted keys and preserves unicode characters.
    """

    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def sha256_json_cache_key(prefix: str, payload: Any) -> str:
    """Build a deterministic cache key for a JSON-serializable payload."""

    digest = hashlib.sha256(json_dumps_deterministic(payload).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def speaker_role_mapping_cache_key(*, utterances: list[dict[str, Any]], prompt_id: str) -> str:
    """Cache key for speaker->role mapping results."""

    payload = {"prompt_id": prompt_id, "utterances": utterances}
    return sha256_json_cache_key("speaker_role_mapping", payload)


def utterance_tagging_cache_key(*, utterances: list[dict[str, Any]], prompt_id: str) -> str:
    """Cache key for utterance tagging results."""

    payload = {"prompt_id": prompt_id, "utterances": utterances}
    return sha256_json_cache_key("utterance_tagging", payload)


def llm_chunk_cache_key(*, chunk: str, prompt_id: str) -> str:
    """Cache key for LLM chunk analysis results.

    Matches the previous behavior in LLMAnalysisBackend.
    """

    combined = f"{chunk}:{prompt_id}"
    hash_digest = hashlib.md5(combined.encode()).hexdigest()
    return f"llm_chunk_{hash_digest}"
