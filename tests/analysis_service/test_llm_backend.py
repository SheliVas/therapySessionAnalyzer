import pytest
from typing import Dict, Any
from src.analysis_service.llm_backend import LLMAnalysisBackend
from src.analysis_service.llm_client import LLMClient
from src.analysis_service.domain import AnalysisResult

class FakeLLMClient(LLMClient):
    def __init__(self, return_value: Dict[str, Any]):
        self.return_value = return_value

    def analyze_transcript(self, transcript_text: str) -> Dict[str, Any]:
        return self.return_value

@pytest.fixture
def fake_llm_result():
    return {"summary": "short summary", "topics": ["topic1", "topic2"]}

@pytest.fixture
def fake_llm_client(fake_llm_result):
    return FakeLLMClient(return_value=fake_llm_result)

@pytest.fixture
def backend(fake_llm_client):
    return LLMAnalysisBackend(llm_client=fake_llm_client)

@pytest.mark.unit
def test_should_return_analysis_result_with_llm_data_when_transcript_is_valid(backend, fake_llm_result):
    transcript_text = "hello world hello"
    result = backend.analyze(transcript_text)

    assert isinstance(result, AnalysisResult)
    assert result.word_count == 3
    assert result.extra["backend"] == "llm"
    assert result.extra["llm_result"] == fake_llm_result
    assert result.video_id is not None

@pytest.mark.unit
def test_should_return_zero_word_count_when_transcript_is_empty(backend, fake_llm_result):
    transcript_text = ""
    result = backend.analyze(transcript_text)

    assert isinstance(result, AnalysisResult)
    assert result.word_count == 0
    assert result.extra["backend"] == "llm"
    assert result.extra["llm_result"] == fake_llm_result

@pytest.mark.unit
def test_should_return_zero_word_count_when_transcript_is_whitespace_only(backend, fake_llm_result):
    transcript_text = "   \n  \t "
    result = backend.analyze(transcript_text)

    assert isinstance(result, AnalysisResult)
    assert result.word_count == 0
    assert result.extra["backend"] == "llm"
    assert result.extra["llm_result"] == fake_llm_result

@pytest.mark.unit
def test_should_propagate_exception_when_llm_client_fails():
    class FailingLLMClient(LLMClient):
        def analyze_transcript(self, transcript_text: str) -> Dict[str, Any]:
            raise RuntimeError("LLM API is down")

    backend = LLMAnalysisBackend(llm_client=FailingLLMClient())
    
    with pytest.raises(RuntimeError, match="LLM API is down"):
        backend.analyze("some text")

