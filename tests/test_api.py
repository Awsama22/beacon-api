from fastapi.testclient import TestClient

from application import application
from configurations.environment_config import environment
from constants.firms_constants import FirmsSource
from services.ingestion_service import archive_url, area_url, near_real_time_url
from validators.ingestion_validator import AreaIngestionRequest

client = TestClient(application)


def test_health_returns_service():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["data"]["service"] == "natoor-api"
    assert response.json()["data"]["database"] in ("ok", "unavailable")


def test_unknown_route_returns_404():
    response = client.get("/health/missing")
    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Route not found"


def test_reversed_box_is_rejected():
    response = client.get("/fires", params={"west": 10, "south": 0, "east": 5, "north": 10})
    assert response.status_code == 422
    assert "west must be less than east" in response.json()["error"]["details"][0]["message"]


def test_near_real_time_rejects_archive_sources():
    response = client.post("/ingestions/firms/near-real-time", json={"sources": ["MODIS_SP"]})
    assert response.status_code == 422


def test_area_needs_map_key(monkeypatch):
    monkeypatch.setattr(environment, "FIRMS_MAP_KEY", "")
    body = {
        "source": "VIIRS_NOAA20_NRT",
        "bbox": {"west": 50, "south": 20, "east": 60, "north": 30},
    }
    response = client.post("/ingestions/firms/area", json=body)
    assert response.status_code == 400


def test_ingestion_needs_admin_key_when_set(monkeypatch):
    monkeypatch.setattr(environment, "ADMIN_API_KEY", "secret")
    assert client.get("/ingestions").status_code == 401
    response = client.get("/ingestions/not-a-uuid", headers={"X-Admin-Key": "secret"})
    assert response.status_code == 422


def test_firms_urls():
    base = environment.FIRMS_BASE_URL
    assert near_real_time_url(FirmsSource.VIIRS_NOAA20_NRT, "24h") == (
        f"{base}/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv"
    )
    assert archive_url(FirmsSource.MODIS_SP, "Oman", 2010) == (
        f"{base}/data/country/modis/2010/modis_2010_Oman.csv"
    )
    request = AreaIngestionRequest.model_validate(
        {"source": "MODIS_NRT", "bbox": {"west": 1, "south": 2, "east": 3, "north": 4}}
    )
    assert area_url(request).endswith("/MODIS_NRT/1.0,2.0,3.0,4.0/1")


def test_near_real_time_sources_are_deduplicated():
    from validators.ingestion_validator import NearRealTimeIngestionRequest

    request = NearRealTimeIngestionRequest(sources=["MODIS_NRT"] * 50)
    assert request.sources == ["MODIS_NRT"]
