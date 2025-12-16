from fastapi import FastAPI, UploadFile, File, status, HTTPException
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
from pymongo import MongoClient

from src.upload_service.domain import VideoEventPublisher, VideosRepository, handle_video_upload
from src.upload_service.config import get_rabbitmq_config, get_minio_config, get_mongo_config
from src.upload_service.storage import StorageClient
from src.upload_service.rabbitmq_publisher import RabbitMQVideoEventPublisher
from src.shared.minio_storage import MinioStorage
from src.shared.videos_repository import MongoVideosRepository


class VideoUploadResponse(BaseModel):
    video_id: str
    filename: str


def create_production_app() -> FastAPI:
    storage_client = MinioStorage(get_minio_config())
    publisher = RabbitMQVideoEventPublisher(get_rabbitmq_config())
    
    mongo_config = get_mongo_config()
    mongo_client = MongoClient(mongo_config.uri)
    repository = MongoVideosRepository(mongo_client, mongo_config.db_name)
    
    return create_app(
        storage_client=storage_client,
        publisher=publisher,
        repository=repository,
    )


def create_app(
    storage_client: StorageClient,
    publisher: VideoEventPublisher,
    repository: VideosRepository,
) -> FastAPI:
    app = FastAPI(title="Upload Service")

    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    @app.post(
        "/videos",
        status_code=status.HTTP_201_CREATED,
        response_model=VideoUploadResponse,
    )
    async def upload_video(file: UploadFile = File(...)) -> VideoUploadResponse:
        """Upload a video file and publish an event."""
        content = await file.read()
        
        try:
            video_id = handle_video_upload(
                storage_client=storage_client,
                publisher=publisher,
                repository=repository,
                filename=file.filename,
                content=content,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            raise HTTPException(status_code=500, detail="Service unavailable")
        
        return VideoUploadResponse(video_id=video_id, filename=file.filename)

    return app