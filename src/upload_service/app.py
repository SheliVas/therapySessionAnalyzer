from fastapi import FastAPI, UploadFile, File, status
from pydantic import BaseModel
import uuid
from pathlib import Path 

class VideoUploadResponse(BaseModel):
    video_id: str
    filename: str


def create_app() -> FastAPI:
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
        video_id = str(uuid.uuid4())
        base_dir = Path("data") / "uploads" / video_id
        base_dir.mkdir(parents=True, exist_ok=True)

        target_path = base_dir / file.filename
        content = await file.read()
        target_path.write_bytes(content)

        return VideoUploadResponse(
            video_id=video_id,
            filename=file.filename,
        )

    return app


app = create_app()
