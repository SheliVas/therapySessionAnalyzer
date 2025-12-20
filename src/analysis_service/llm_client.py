import json
import logging
import time
from typing import Any, Dict, Optional, Union, Protocol

import httpx

logger = logging.getLogger(__name__)


PromptInput = Union[str, Dict[str, str]]


class LLMClient(Protocol):
    def analyze_transcript(self, transcript_text: PromptInput) -> Dict[str, Any]:
        """Analyze the transcript text and return a dictionary of results."""
        ...


class GeminiLLMClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        base_url: str = "https://generativelanguage.googleapis.com",
        timeout: float = 180.0,
    ):
        if not api_key:
            raise ValueError("API key must be provided for GeminiLLMClient")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def analyze_transcript(self, transcript_text: PromptInput) -> Dict[str, Any]:
        system_instruction: Optional[str] = None
        user_prompt: Optional[str] = None

        if isinstance(transcript_text, dict):
            system_instruction = transcript_text.get("system_prompt") or transcript_text.get("system")
            user_prompt = (
                transcript_text.get("user_prompt")
                or transcript_text.get("user")
                or transcript_text.get("prompt")
                or transcript_text.get("content")
            )
        elif isinstance(transcript_text, str):
            user_prompt = transcript_text
        else:
            raise TypeError("transcript_text must be a string or dict containing prompt text")

        if user_prompt is not None and not isinstance(user_prompt, str):
            raise ValueError("User prompt text must be a string for GeminiLLMClient")
        if system_instruction is not None and not isinstance(system_instruction, str):
            raise ValueError("System prompt text must be a string for GeminiLLMClient")

        if not user_prompt:
            raise ValueError("User prompt text must be provided for GeminiLLMClient")

        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}],
            }

        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
        started_at = time.perf_counter()
        logger.info("llm_client.request.start model=%s", self.model)
        
        max_retries = 5
        base_delay = 2.0
        
        with httpx.Client(timeout=self.timeout) as client:
            for attempt in range(max_retries):
                try:
                    response = client.post(
                        url,
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    logger.info(
                        "llm_client.request.success model=%s status=%s duration=%.2fs",
                        self.model,
                        response.status_code,
                        time.perf_counter() - started_at,
                    )
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        if attempt == max_retries - 1:
                            logger.error("llm_client.request.failed_max_retries model=%s error=%s", self.model, e)
                            raise
                        
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            "llm_client.request.rate_limited model=%s attempt=%d/%d delay=%.2fs",
                            self.model,
                            attempt + 1,
                            max_retries,
                            delay,
                        )
                        time.sleep(delay)
                    else:
                        raise

        try:
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Invalid response structure from Gemini API") from exc

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM output was not valid JSON") from exc


def get_llm_client(api_key: Optional[str], model: str, base_url: str, timeout: float) -> LLMClient:
    if not api_key:
        raise ValueError("API key must be provided to create an LLM client")
    return GeminiLLMClient(api_key=api_key, model=model, base_url=base_url, timeout=timeout)
