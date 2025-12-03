from fastapi import FastAPI, HTTPException
from abc import ABC, abstractmethod
from src.report_service.mongo_repository import VideoSummary


class ReportRepository(ABC):
    @abstractmethod
    def list_videos(self) -> list[VideoSummary]:
        pass

    @abstractmethod
    def get_video(self, video_id: str) -> VideoSummary | None:
        pass


class NoOpReportRepository(ReportRepository):
    def list_videos(self) -> list[VideoSummary]:
        return []

    def get_video(self, video_id: str) -> VideoSummary | None:
        return None


def create_app(report_repository: ReportRepository | None = None) -> FastAPI:
    if report_repository is None:
        report_repository = NoOpReportRepository()
    
    app = FastAPI(title="Report Service")

    @app.get("/health")
    def health_check():
        return {"status": "ok"}

    @app.get("/videos")
    def get_videos() -> list[VideoSummary]:
        return report_repository.list_videos()

    @app.get("/videos/{video_id}")
    def get_video(video_id: str) -> VideoSummary:
        video = report_repository.get_video(video_id)
        if video is None:
            raise HTTPException(status_code=404, detail="Video not found")
        return video

    return app


app = create_app()
