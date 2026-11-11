"""Trusted local UI session bootstrap."""
from fastapi import APIRouter, Response

from app.core.api_auth import set_api_session_cookie

router = APIRouter()


@router.post("/bootstrap", status_code=204)
async def bootstrap_session(response: Response) -> Response:
    """Set an HttpOnly process-token cookie for an origin-validated Aegis UI."""
    set_api_session_cookie(response)
    response.status_code = 204
    return response
