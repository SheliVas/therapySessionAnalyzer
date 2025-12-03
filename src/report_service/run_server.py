from pymongo import MongoClient

from src.report_service.app import create_app
from src.report_service.config import load_config
from src.report_service.mongo_repository import MongoReportRepository


config = load_config()

_client = MongoClient(config.mongo_uri)
_repo = MongoReportRepository(_client, db_name=config.mongo_db_name)

app = create_app(_repo)
