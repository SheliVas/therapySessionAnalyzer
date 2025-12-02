from fastapi import FastAPI


def create_app() -> FastAPI:
    application = FastAPI(title="Analysis Service")

    @application.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return application


app = create_app()
