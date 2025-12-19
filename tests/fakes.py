from typing import Optional, Any

class FakeVideoEventPublisher:
    """Global fake publisher for upload service tests."""
    def __init__(self) -> None:
        self.published: list[Any] = []
        self.published_events: list[Any] = [] # Alias for compatibility

    def publish_video_uploaded(self, event: Any) -> None:
        self.published.append(event)
        self.published_events.append(event)


class FakeStorageClient:
    """Unified fake StorageClient that records download/upload calls and manages in-memory files."""
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.download_called_with: Optional[dict] = None
        self.upload_called_with: Optional[dict] = None
        self.upload_calls: list[tuple[str, str, bytes]] = [] # For analysis service compatibility
        self.uploads: list[dict] = [] # For upload service compatibility
        self._default_download_response: bytes = b""
    
    def set_download_response(self, content: bytes) -> None:
        """Set the response for download_file calls (legacy support)."""
        self._default_download_response = content
    
    def download_file(self, bucket: str, key: str) -> bytes:
        """Record the call and return the file content."""
        self.download_called_with = {"bucket": bucket, "key": key}
        path = f"{bucket}/{key}"
        if path in self.files:
            return self.files[path]
        return self._default_download_response
    
    def upload_file(self, bucket: str, key: str, content: bytes) -> None:
        """Record the upload call."""
        path = f"{bucket}/{key}"
        self.files[path] = content
        self.upload_called_with = {"bucket": bucket, "key": key, "content": content}
        
        # Compatibility with analysis service
        self.upload_calls.append((bucket, key, content))
        
        # Compatibility with upload service
        self.uploads.append({
            "bucket": bucket,
            "key": key,
            "content_length": len(content),
        })

    def add_file(self, bucket: str, key: str, content: bytes) -> None:
        """Helper to add a file to the fake storage."""
        path = f"{bucket}/{key}"
        self.files[path] = content


class FakeVideosRepository:
    """Unified fake repository for testing video status updates."""
    def __init__(self) -> None:
        self.mark_audio_extracted_calls: list[dict] = []
        self.mark_transcribed_calls: list[dict] = []
        self.mark_analyzed_calls: list[dict] = []
        self.should_raise_error = False
        self.videos: list[dict] = [] # For upload service compatibility
    
    def mark_audio_extracted(self, video_id: str, audio_path: str) -> None:
        """Record mark_audio_extracted call."""
        self.mark_audio_extracted_calls.append({
            "video_id": video_id,
            "audio_path": audio_path,
        })
        if self.should_raise_error:
            raise ValueError("Repository error")
    
    def mark_transcribed(self, video_id: str, transcript_path: str) -> None:
        """Record mark_transcribed call."""
        self.mark_transcribed_calls.append({
            "video_id": video_id,
            "transcript_path": transcript_path,
        })
        if self.should_raise_error:
            raise ValueError("Repository error")
    
    def mark_analyzed(self, video_id: str, word_count: int) -> None:
        """Record mark_analyzed call."""
        self.mark_analyzed_calls.append({
            "video_id": video_id,
            "word_count": word_count,
        })
        if self.should_raise_error:
            raise ValueError("Repository error")

    def upsert_on_upload(
        self,
        video_id: str,
        filename: str,
        storage_path: str,
        uploaded_at: Any,
    ) -> None:
        self.videos.append({
            "video_id": video_id,
            "filename": filename,
            "storage_path": storage_path,
            "uploaded_at": uploaded_at,
        })
