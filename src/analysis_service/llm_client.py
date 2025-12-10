from typing import Protocol, Dict, Any

class LLMClient(Protocol):
    def analyze_transcript(self, transcript_text: str) -> Dict[str, Any]:
        """Analyze the transcript text and return a dictionary of results."""
        ...
