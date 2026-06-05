"""Date list API endpoint."""

from fastapi import APIRouter

from server.services.review_queries import get_connection, get_dates

router = APIRouter()


@router.get("/api/dates")
def get_available_dates():
    """Return list of available trade dates (newest first)."""
    conn = get_connection()
    try:
        dates = get_dates(conn)
        return {"dates": dates}
    finally:
        conn.close()
