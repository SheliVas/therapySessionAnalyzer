import pytest
from typing import Dict, Any
from src.analysis_service.llm_backend import LLMAnalysisBackend
from src.analysis_service.llm_client import LLMClient
from src.analysis_service.domain import AnalysisResult
from tests.analysis_service.conftest import FakeLLMClient


@pytest.fixture
def backend(fake_llm_client: FakeLLMClient) -> LLMAnalysisBackend:
    return LLMAnalysisBackend(llm_client=fake_llm_client)


@pytest.mark.unit
@pytest.mark.parametrize(
    "transcript_text,expected_word_count",
    [
        ("hello world hello", 3),
        ("", 0),
        ("   \n  \t ", 0),
    ]
)
def test_should_return_result_with_correct_word_count(
    backend: LLMAnalysisBackend,
    fake_llm_result: Dict[str, Any],
    transcript_text: str,
    expected_word_count: int,
) -> None:
    result = backend.analyze(transcript_text)

    assert result.word_count == expected_word_count
    assert result.extra["backend"] == "llm"
    assert result.extra["llm_result"] == fake_llm_result
    assert result.video_id is not None


@pytest.mark.unit
def test_should_propagate_exception_when_llm_client_fails() -> None:
    class FailingLLMClient(LLMClient):
        def analyze_transcript(self, transcript_text: str) -> Dict[str, Any]:
            raise RuntimeError("LLM API is down")

    backend = LLMAnalysisBackend(llm_client=FailingLLMClient())
    
    with pytest.raises(RuntimeError, match="LLM API is down"):
        backend.analyze("some text")
