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
    assert "report_count" in data
    assert "company_count" in data
    assert "latest_upload_date" in data 