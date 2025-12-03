import os
from pydantic import BaseModel


class ReportServiceConfig(BaseModel):
    mongo_uri: str
    mongo_db_name: str


def load_config() -> ReportServiceConfig:
    mongo_uri = os.getenv("MONGO_URI", "mongodb://mongo:27017/")
    mongo_db_name = os.getenv("MONGO_DB_NAME", "therapy_analysis")

    return ReportServiceConfig(
        mongo_uri=mongo_uri,
        mongo_db_name=mongo_db_name,
    )
