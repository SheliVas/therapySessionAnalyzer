import os
import pytest
from src.upload_service.config import get_mongo_config

@pytest.mark.unit
def test_should_load_upload_mongo_config_from_env_vars(mocker):
    mocker.patch.dict(os.environ, {
        "MONGO_URI": "mongodb://mongo:27017",
        "MONGO_DB": "upload-db"
    })
    
    config = get_mongo_config()
    
    assert config.uri == "mongodb://mongo:27017"
    assert config.db_name == "upload-db"
