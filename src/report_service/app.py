from fastapi import FastAPI
from abc import ABC, abstractmethod
from src.report_service.mongo_repository import VideoSummary


class ReportRepository(ABC):
    @abstractmethod
    def list_videos(self) -> list[VideoSummary]:
        pass


class NoOpReportRepository(ReportRepository):
    def list_videos(self) -> list[VideoSummary]:
        return []


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

    return app


app = create_app()
