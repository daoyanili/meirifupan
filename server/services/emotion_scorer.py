"""Emotion scoring model for market review.

Scores 5 indicators (each 0-3) and computes a weighted average
to produce an overall market emotion level.
"""

from __future__ import annotations

import sqlite3
from typing import Any


# Default limit-down count when sentiment_daily data is missing
DEFAULT_LIMIT_DOWN = 3

# Scoring thresholds: list of (upper_bound, score)
# The first threshold whose value < upper_bound applies
LIMIT_UP_THRESHOLDS = [(30, 0), (60, 1), (100, 2), (float("inf"), 3)]
FIRST_BOARD_THRESHOLDS = [(20, 0), (50, 1), (80, 2), (float("inf"), 3)]
LIMIT_RATIO_THRESHOLDS = [(2, 0), (5, 1), (10, 2), (float("inf"), 3)]


def _threshold_score(value: float, thresholds: list[tuple[float, int]]) -> int:
    """Map a numeric value to a score based on thresholds."""
    for upper, score in thresholds:
        if value < upper:
            return score
    return thresholds[-1][1]


def _board_height_score(highest_board: int) -> int:
    """Score based on highest consecutive board count."""
    if highest_board < 3:
        return 0
    if highest_board == 3:
        return 1
    if highest_board == 4:
        return 2
    return 3


def _market_change_score(change_pct: float) -> int:
    """Score based on major index daily change percentage."""
    if change_pct < -1.0:
        return 0
    if change_pct <= 0:
        return 1
    if change_pct < 1.0:
        return 2
    return 3


def _emotion_level(score: float) -> dict[str, str]:
    """Map weighted score to emotion level and advice."""
    if score < 0.8:
        return {"level": "冰点", "advice": "空仓等待，寻找错杀机会"}
    if score < 1.5:
        return {"level": "低迷", "advice": "轻仓试错，只做确定性高的"}
    if score < 2.2:
        return {"level": "中性", "advice": "正常仓位，跟随主线"}
    if score < 2.7:
        return {"level": "亢奋", "advice": "控制仓位，注意高位风险"}
    return {"level": "过热", "advice": "减仓，准备撤退"}


def compute_emotion(
    conn: sqlite3.Connection,
    date: str,
    stats: dict[str, Any] | None = None,
    indices: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compute emotion score for a given date.

    Args:
        conn: Database connection.
        date: Trade date string (YYYY-MM-DD).
        stats: Pre-fetched limit-up stats (optional, will query if not provided).
        indices: Pre-fetched index data (optional, will query if not provided).

    Returns:
        Dict with scores, total_score, level, advice.
    """
    # --- 1. Limit-up count ---
    if stats is None:
        from server.services.review_queries import get_limit_up_stats
        stats = get_limit_up_stats(conn, date)

    total = stats.get("total", 0)
    first_board = stats.get("first_board", 0)
    highest_board = stats.get("highest_board", 1)

    # --- 2. Market index change ---
    if indices is None:
        from server.services.review_queries import get_indices
        indices = get_indices(conn, date)

    # Use Shanghai Composite (000001.SS) as primary reference, fallback to first index
    market_change = 0.0
    for idx in indices:
        if idx.get("index_code") in ("000001.SS", "1A0001"):
            market_change = idx.get("change_pct") or 0.0
            break
    if market_change == 0.0 and indices:
        market_change = indices[0].get("change_pct") or 0.0

    # --- 3. Limit-up / limit-down ratio ---
    limit_down = DEFAULT_LIMIT_DOWN
    limit_ratio = total / limit_down if limit_down > 0 else total

    # --- 4. Compute individual scores ---
    scores = {
        "limit_up_count": {
            "value": total,
            "score": _threshold_score(total, LIMIT_UP_THRESHOLDS),
            "weight": 0.30,
            "label": "涨停数",
        },
        "board_height": {
            "value": highest_board,
            "score": _board_height_score(highest_board),
            "weight": 0.25,
            "label": "连板高度",
        },
        "first_board_count": {
            "value": first_board,
            "score": _threshold_score(first_board, FIRST_BOARD_THRESHOLDS),
            "weight": 0.20,
            "label": "首板数",
        },
        "limit_ratio": {
            "value": round(limit_ratio, 2),
            "score": _threshold_score(limit_ratio, LIMIT_RATIO_THRESHOLDS),
            "weight": 0.15,
            "label": "涨跌停比",
        },
        "market_change": {
            "value": market_change,
            "score": _market_change_score(market_change),
            "weight": 0.10,
            "label": "大盘涨跌",
        },
    }

    # --- 5. Weighted total ---
    total_score = sum(
        item["score"] * item["weight"] for item in scores.values()
    )
    total_score = round(total_score, 2)

    emotion = _emotion_level(total_score)

    return {
        "date": date,
        "scores": scores,
        "total_score": total_score,
        "level": emotion["level"],
        "advice": emotion["advice"],
    }
