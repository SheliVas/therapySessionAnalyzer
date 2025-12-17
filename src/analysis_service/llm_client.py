import json
import httpx
from typing import Protocol, Dict, Any, Optional

class LLMClient(Protocol):
    def analyze_transcript(self, transcript_text: str) -> Dict[str, Any]:
        """Analyze the transcript text and return a dictionary of results."""
        ...

class OpenAILLMClient(LLMClient):
    def __init__(self, api_key: str, model: str, base_url: str, timeout: float):
        if not api_key:
            raise ValueError("API key must be provided for OpenAILLMClient")
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    def analyze_transcript(self, transcript_text: str) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Analyze the following therapy session transcript. Return a JSON object with 'emotion' and 'summary' keys."
                },
                {
                    "role": "user",
                    "content": transcript_text
                }
            ],
            "response_format": {"type": "json_object"}
        }

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)

def get_llm_client(api_key: Optional[str], model: str, base_url: str, timeout: float) -> LLMClient:
    if not api_key:
        raise ValueError("API key must be provided to create an LLM client")
    return OpenAILLMClient(api_key=api_key, model=model, base_url=base_url, timeout=timeout)
