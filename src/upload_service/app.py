from fastapi import FastAPI, UploadFile, File, status
from pydantic import BaseModel
import uuid
from pathlib import Path

from src.upload_service.domain import VideoEventPublisher, VideoUploadedEvent
from src.upload_service.config import get_rabbitmq_config
from src.upload_service.rabbitmq_publisher import RabbitMQVideoEventPublisher



class VideoUploadResponse(BaseModel):
    video_id: str
    filename: str


class NoOpVideoEventPublisher:
    def publish_video_uploaded(self, event: VideoUploadedEvent) -> None:
        # Stub implementation: do nothing for now
        pass


def create_production_app() -> FastAPI:
    config = get_rabbitmq_config()
    publisher = RabbitMQVideoEventPublisher(config)
    return create_app(publisher)


def create_app(publisher: VideoEventPublisher | None = None) -> FastAPI:
    app = FastAPI(title="Upload Service")

    if publisher is None:
        publisher = NoOpVideoEventPublisher()

    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    @app.post(
        "/videos",
        status_code=status.HTTP_201_CREATED,
        response_model=VideoUploadResponse,
    )
    async def upload_video(file: UploadFile = File(...)) -> VideoUploadResponse:
        video_id = str(uuid.uuid4())
        base_dir = Path("data") / "uploads" / video_id
        base_dir.mkdir(parents=True, exist_ok=True)

        target_path = base_dir / file.filename
        content = await file.read()
        target_path.write_bytes(content)
        
        event = VideoUploadedEvent(
            video_id=video_id,
            filename=file.filename,
            storage_path=str(target_path),
        )

        publisher.publish_video_uploaded(event)

        return VideoUploadResponse(
            video_id=video_id,
            filename=file.filename,
        )

    return app


app = create_app()