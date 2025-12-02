from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create and configure the transcription service FastAPI application."""
    application = FastAPI(title="Transcription Service")

    @application.get("/health")
    def health():
        return {"status": "ok"}

    return application


app = create_app()
