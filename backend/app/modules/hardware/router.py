from fastapi import APIRouter

router = APIRouter(prefix="/hardware", tags=["hardware"])


@router.get("/status")
def status():
    return {"enabled": True, "adapters": [], "note": "hardware_module_not_implemented"}
