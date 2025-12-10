from src.analysis_service.domain import AnalysisBackend, AnalysisResult
from src.analysis_service.llm_client import LLMClient

class LLMAnalysisBackend(AnalysisBackend):
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def analyze(self, transcript_text: str) -> AnalysisResult:
        word_count = len(transcript_text.split())
        llm_result = self.llm_client.analyze_transcript(transcript_text)
        
        return AnalysisResult(
            video_id="", # TODO: inspect this later, might be wrong approach.
            word_count=word_count,
            extra={
                "backend": "llm",
                "llm_result": llm_result
            }
        )
