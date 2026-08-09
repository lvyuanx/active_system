from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}

