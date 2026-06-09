"""Review data API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from server.services.emotion_scorer import compute_emotion
from server.services.review_queries import (
    get_all_stocks,
    get_board_advancement,
    get_board_tiers,
    get_capital_flow,
    get_dates,
    get_emotion_heat_trend,
    get_high_stocks,
    get_hot_boards_rank,
    get_hot_plates,
    get_hot_stocks_derived,
    get_hot_stocks_rank,
    get_hot_available_dates,
    get_indices,
    get_latest_data_job,
    get_limit_up_stats,
    get_market_environment,
    get_market_overview_trend,
    get_quantzz_daily_overview,
    get_connection,
    get_recent_dates,
    get_saved_review,
    get_seal_quality,
)

router = APIRouter()


@router.get("/api/review")
def get_review(date: str = Query(..., description="Trade date, e.g. 2026-06-03")):
    """Return full review data for a given date."""
    conn = get_connection()
    try:
        available = get_dates(conn)
        if date not in available:
            raise HTTPException(
                status_code=404,
                detail=f"No data for date {date}. Available: {available[:5]}...",
            )

        indices = get_indices(conn, date)
        stats = get_limit_up_stats(conn, date)
        board_tiers = get_board_tiers(conn, date)
        hot_plates = get_hot_plates(conn, date)
        high_stocks = get_high_stocks(conn, date)
        all_stocks = get_all_stocks(conn, date)
        market_environment = get_market_environment(conn, date)
        saved_review = get_saved_review(conn, date)
        emotion = compute_emotion(conn, date, stats=stats, indices=indices)

        return {
            "date": date,
            "indices": indices,
            "limit_up_stats": stats,
            "market_environment": market_environment,
            "saved_review": saved_review,
            "board_tiers": board_tiers,
            "hot_plates": hot_plates,
            "high_stocks": high_stocks,
            "all_stocks": all_stocks,
            "emotion": emotion,
        }
    finally:
        conn.close()


@router.get("/api/review/report")
def get_review_report(date: str = Query(..., description="Trade date, e.g. 2026-06-03")):
    """Return the generated review report for a given date."""
    conn = get_connection()
    try:
        review = get_saved_review(conn, date)
        if not review:
            raise HTTPException(status_code=404, detail=f"No generated review for date {date}.")
        return review
    finally:
        conn.close()


@router.get("/api/emotion/trend")
def get_emotion_trend(
    date: str = Query(..., description="End date, e.g. 2026-06-03"),
    days: int = Query(5, description="Number of trading days to include"),
):
    """Return emotion scores for recent N trading days."""
    conn = get_connection()
    try:
        available = get_dates(conn)
        if date not in available:
            raise HTTPException(
                status_code=404,
                detail=f"No data for date {date}.",
            )

        recent_dates = get_recent_dates(conn, date, days)
        trend = []
        for d in recent_dates:
            stats = get_limit_up_stats(conn, d)
            indices = get_indices(conn, d)
            emotion = compute_emotion(conn, d, stats=stats, indices=indices)
            trend.append(emotion)

        # Sort by date ascending for chart display
        trend.sort(key=lambda x: x["date"])

        return {
            "date": date,
            "days": days,
            "trend": trend,
        }
    finally:
        conn.close()


@router.get("/api/emotion/heat-trend")
def get_emotion_heat(
    date: str = Query(..., description="End date, e.g. 2026-06-03"),
    days: int = Query(60, description="Number of trading days to include"),
):
    """Return daily heat metrics for sentiment, hot stocks and space-board review."""
    conn = get_connection()
    try:
        return {
            "date": date,
            "days": days,
            "trend": get_emotion_heat_trend(conn, date, days),
        }
    finally:
        conn.close()


@router.get("/api/quantzz/daily")
def get_quantzz_daily(
    date: str = Query(..., description="Trade date, e.g. 2026-06-03"),
    days: int = Query(60, description="Number of trading days to include"),
):
    """Return a Quantzz-style daily overview built from daily-level data."""
    conn = get_connection()
    try:
        available = get_dates(conn)
        if date not in available:
            raise HTTPException(status_code=404, detail=f"No data for date {date}.")
        return get_quantzz_daily_overview(conn, date, days)
    finally:
        conn.close()


@router.get("/api/market/overview-trend")
def get_market_trend(
    date: str = Query(..., description="End date, e.g. 2026-06-03"),
    days: int = Query(5, description="Number of trading days to include"),
):
    """Return recent market overview metrics."""
    conn = get_connection()
    try:
        available = get_dates(conn)
        if date not in available:
            raise HTTPException(status_code=404, detail=f"No data for date {date}.")
        return {
            "date": date,
            "days": days,
            "trend": get_market_overview_trend(conn, date, days),
        }
    finally:
        conn.close()


@router.get("/api/insights")
def get_insights(date: str = Query(..., description="Trade date, e.g. 2026-06-03")):
    """Return market insights: seal quality, board advancement, capital flow, hot stocks."""
    conn = get_connection()
    try:
        available = get_dates(conn)
        if date not in available:
            raise HTTPException(
                status_code=404,
                detail=f"No data for date {date}.",
            )

        seal_quality = get_seal_quality(conn, date)
        board_advancement = get_board_advancement(conn, date)
        capital_flow = get_capital_flow(conn, date)
        hot_stocks = get_hot_stocks_derived(conn, date)

        return {
            "date": date,
            "seal_quality": seal_quality,
            "board_advancement": board_advancement,
            "capital_flow": capital_flow,
            "hot_stocks": hot_stocks,
        }
    finally:
        conn.close()


@router.get("/api/hot")
def get_hot(date: str = Query(..., description="Trade date, e.g. 2026-06-03")):
    """Return hot stocks and hot boards for a given date."""
    conn = get_connection()
    try:
        hot_stocks = get_hot_stocks_rank(conn, date, limit=30)
        concept_boards = get_hot_boards_rank(conn, date, board_type="concept", limit=20)
        industry_boards = get_hot_boards_rank(conn, date, board_type="industry", limit=20)

        return {
            "date": date,
            "hot_stocks": hot_stocks,
            "concept_boards": concept_boards,
            "industry_boards": industry_boards,
        }
    finally:
        conn.close()


@router.get("/api/hot/dates")
def get_hot_dates():
    """Return available dates for hot data."""
    conn = get_connection()
    try:
        dates = get_hot_available_dates(conn)
        return {"dates": dates}
    finally:
        conn.close()


@router.get("/api/jobs/latest")
def get_latest_job(job_name: str = Query("daily_update", description="Job name")):
    """Return latest data update job status."""
    conn = get_connection()
    try:
        job = get_latest_data_job(conn, job_name)
        if not job:
            raise HTTPException(status_code=404, detail=f"No job records for {job_name}.")
        return job
    finally:
        conn.close()
