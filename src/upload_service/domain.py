from typing import Protocol

from pydantic import BaseModel


class VideoUploadedEvent(BaseModel):
    video_id: str
    filename: str
    storage_path: str


class VideoEventPublisher(Protocol):
    def publish_video_uploaded(self, event: VideoUploadedEvent) -> None:
        return