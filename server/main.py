"""FastAPI entry point for the market review API."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.dates import router as dates_router
from server.api.review import router as review_router

app = FastAPI(title="发家致富 API", description="A股复盘系统后端接口")

# CORS - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(dates_router)
app.include_router(review_router)


@app.get("/api/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


# Production: serve frontend static files if web/dist exists
web_dist = os.path.join(os.path.dirname(__file__), "..", "web", "dist")
if os.path.exists(web_dist):
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=web_dist, html=True))
