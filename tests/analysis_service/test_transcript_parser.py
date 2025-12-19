import pytest
from src.analysis_service.transcript_parser import parse_transcript

@pytest.mark.unit
@pytest.mark.parametrize(
    "transcript,expected_count",
    [
        ("Speaker A: Hello", 1),
        ("Speaker A: Hello\nSpeaker B: Hi", 2),
        ("Speaker A: Hello\n\nSpeaker B: Hi", 2),
    ]
)
def test_should_parse_transcript_into_utterances(
    transcript: str,
    expected_count: int,
) -> None:
    """Transcript should be parsed into utterances."""
    utterances = parse_transcript(transcript)
    
    assert isinstance(utterances, list)
    assert len(utterances) == expected_count
    for utt in utterances:
        assert "speaker_label" in utt
        assert "text" in utt
        assert "index" in utt
