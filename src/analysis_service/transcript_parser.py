from typing import List, Dict, Any

def parse_transcript(transcript_text: str) -> List[Dict[str, Any]]:
    """Parse transcript into utterances (speaker_label + text)."""
    utterances = []
    lines = transcript_text.strip().split('\n')
    index = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if ':' in line:
            speaker_part, text_part = line.split(':', 1)
            utterances.append({
                "index": index,
                "speaker_label": speaker_part.strip(),
                "text": text_part.strip()
            })
            index += 1
    return utterances
