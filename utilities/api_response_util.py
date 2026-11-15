from typing import Any


def success_response(data: Any) -> dict:
    return {"success": True, "data": data, "error": None}


def error_response(message: str, details: Any = None) -> dict:
    error = {"message": message}
    if details is not None:
        error["details"] = details
    return {"success": False, "data": None, "error": error}
