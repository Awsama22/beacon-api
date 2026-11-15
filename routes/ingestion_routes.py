from fastapi import APIRouter, Depends

from controllers import ingestion_controller
from middleware.admin_key_middleware import require_admin_key

ingestion_router = APIRouter(tags=["Ingestions"], dependencies=[Depends(require_admin_key)])
ingestion_router.add_api_route(
    "/firms/near-real-time",
    ingestion_controller.ingest_near_real_time,
    methods=["POST"],
    status_code=202,
    summary="Fetch FIRMS global near-real-time fires (24h, 48h or 7d) into the database",
)
ingestion_router.add_api_route(
    "/firms/area",
    ingestion_controller.ingest_area,
    methods=["POST"],
    status_code=202,
    summary="Fetch fires for a box and date range from the FIRMS Area API (needs FIRMS_MAP_KEY)",
)
ingestion_router.add_api_route(
    "/firms/archive",
    ingestion_controller.ingest_archive,
    methods=["POST"],
    status_code=202,
    summary="Fetch one FIRMS yearly country archive into the database",
)
ingestion_router.add_api_route(
    "/static-sources",
    ingestion_controller.replace_static_sources,
    methods=["POST"],
    summary="Replace the static heat source map (gas flares) and re-mark stored detections",
)
ingestion_router.add_api_route(
    "", ingestion_controller.list_ingestions, methods=["GET"], summary="Latest ingestion runs"
)
ingestion_router.add_api_route(
    "/{run_id}", ingestion_controller.get_ingestion, methods=["GET"], summary="One ingestion run"
)
