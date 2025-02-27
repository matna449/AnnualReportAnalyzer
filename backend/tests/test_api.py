import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Annual Report Analyzer API is running" in response.json()["message"]

def test_get_companies():
    """Test the get_companies endpoint."""
    response = client.get("/api/companies/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_dashboard_summary():
    """Test the dashboard_summary endpoint."""
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_reports" in data
    assert "total_companies" in data
    assert "recent_uploads" in data 