"""Aggregate the v1 API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import analyze, health, reports, simulate, token

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(analyze.router)
api_router.include_router(token.router)
api_router.include_router(simulate.router)
api_router.include_router(reports.router)
