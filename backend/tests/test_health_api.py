import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app import app
from src.services.earth_engine_service import get_ee_status
from src.services.genai_service import get_genai_status

client = TestClient(app)

@pytest.fixture
def mock_ee_status():
    """Mock for Earth Engine status."""
    with patch('src.services.earth_engine_service.get_ee_status') as mock:
        mock.return_value = {
            "initialized": True,
            "error": None
        }
        yield mock

@pytest.fixture
def mock_genai_status():
    """Mock for GenAI status."""
    with patch('src.services.genai_service.get_genai_status') as mock:
        mock.return_value = {
            "initialized": True,
            "error": None,
            "model": "gemma-3-4b-it"
        }
        yield mock

def test_health_check_success(mock_ee_status, mock_genai_status):
    """Test health check endpoint when services are healthy."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["diagnostics"]["ee_initialized"] is True
    assert data["diagnostics"]["llm_initialized"] is True

def test_health_check_degraded_ee(mock_ee_status, mock_genai_status):
    """Test health check endpoint when Earth Engine is not healthy."""
    mock_ee_status.return_value = {
        "initialized": False,
        "error": "Earth Engine initialization failed"
    }
    
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["diagnostics"]["ee_initialized"] is False
    assert data["diagnostics"]["ee_error"] == "Earth Engine initialization failed"

def test_health_check_degraded_genai(mock_ee_status, mock_genai_status):
    """Test health check endpoint when GenAI is not healthy."""
    mock_genai_status.return_value = {
        "initialized": False,
        "error": "GenAI initialization failed",
        "model": None
    }
    
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["diagnostics"]["llm_initialized"] is False
    assert data["diagnostics"]["llm_error"] == "GenAI initialization failed" 