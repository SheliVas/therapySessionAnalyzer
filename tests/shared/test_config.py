import os
import pytest
from src.shared.config import get_minio_config, get_mongo_config

@pytest.mark.unit
def test_should_load_minio_config_from_env_vars(mocker):
    mocker.patch.dict(os.environ, {
        "MINIO_ENDPOINT": "minio:9000",
        "MINIO_ACCESS_KEY": "test-access",
        "MINIO_SECRET_KEY": "test-secret",
        "MINIO_BUCKET": "test-bucket",
        "MINIO_SECURE": "true"
    })
    
    config = get_minio_config()
    
    assert config.endpoint == "minio:9000"
    assert config.access_key == "test-access"
    assert config.secret_key == "test-secret"
    assert config.bucket == "test-bucket"
    assert config.secure is True

@pytest.mark.unit
def test_should_load_mongo_config_from_env_vars(mocker):
    mocker.patch.dict(os.environ, {
        "MONGO_URI": "mongodb://mongo:27017",
        "MONGO_DB": "test-db"
    })
    
    config = get_mongo_config()
    
    assert config.uri == "mongodb://mongo:27017"
    assert config.db_name == "test-db"
