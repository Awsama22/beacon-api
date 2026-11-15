from enum import StrEnum


class IngestionKind(StrEnum):
    NEAR_REAL_TIME = "near_real_time"
    AREA = "area"
    ARCHIVE = "archive"


class IngestionStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


INSERT_BATCH_SIZE = 5000
