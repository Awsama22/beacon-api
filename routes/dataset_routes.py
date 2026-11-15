from fastapi import APIRouter

from constants.dataset_constants import DatasetName
from controllers import dataset_controller

archive_router = APIRouter(tags=["Archive"])
archive_router.add_api_route(
    "/meta",
    dataset_controller.dataset_route(DatasetName.ARCHIVE_META),
    methods=["GET"],
    summary="Archive years, monthly coverage per sensor and sources",
)
archive_router.add_api_route(
    "/countries",
    dataset_controller.dataset_route(DatasetName.ARCHIVE_COUNTRIES),
    methods=["GET"],
    summary="Yearly MODIS, VIIRS and harmonized hot spots per country, with calibration",
)
archive_router.add_api_route(
    "/validation",
    dataset_controller.dataset_route(DatasetName.ARCHIVE_VALIDATION),
    methods=["GET"],
    summary="How well the MODIS-to-VIIRS harmonization holds up on held-out data",
)
archive_router.add_api_route(
    "/tiles/{tile_row}/{tile_col}",
    dataset_controller.archive_tile,
    methods=["GET"],
    summary="One 10° tile of 0.25° cells with monthly MODIS and VIIRS counts since 2000",
)
archive_router.add_api_route(
    "/grid",
    dataset_controller.archive_grid,
    methods=["GET"],
    summary="0.5° harmonized hot spots per year for the globe layer (binary)",
)

history_router = APIRouter(tags=["History"])
history_router.add_api_route(
    "",
    dataset_controller.history,
    methods=["GET"],
    summary="GCC burn history per country and per 0.25° cell",
)

model_router = APIRouter(tags=["Model"])
model_router.add_api_route(
    "",
    dataset_controller.dataset_route(DatasetName.MODEL),
    methods=["GET"],
    summary="The fire-risk model: design, features, weights and test scores",
)
model_router.add_api_route(
    "/sample",
    dataset_controller.dataset_route(DatasetName.MODEL_SAMPLE),
    methods=["GET"],
    summary="A stratified sample of the model's training table",
)
