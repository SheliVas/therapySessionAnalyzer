import os
import pytest
from src.report_service.config import load_config

@pytest.mark.unit
def test_should_load_report_config_from_env_vars(mocker):
    mocker.patch.dict(os.environ, {
        "MONGO_URI": "mongodb://mongo:27017",
        "MONGO_DB": "report-db"
    })
    
    config = load_config()
    
    assert config.mongo_uri == "mongodb://mongo:27017"
    assert config.mongo_db_name == "report-db"
