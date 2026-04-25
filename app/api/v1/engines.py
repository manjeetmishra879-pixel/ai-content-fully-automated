"""
Engine introspection and direct-call endpoints.

Useful for:
* checking which engines are alive (`/engines/health`)
* invoking any engine ad-hoc (`/engines/{name}/run`) — handy for ops/testing.
"""

from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, status

from app.engines import all_engines, get_engine, health_summary, list_engines

router = APIRouter(prefix="/engines", tags=["engines"])


@router.get("/")
async def list_all_engines() -> Dict[str, Any]:
    return {
        "count": len(list_engines()),
        "engines": [
            {"name": e.name, "description": e.description}
            for e in all_engines().values()
        ],
    }


@router.get("/health")
async def engines_health() -> Dict[str, Any]:
    return {"engines": health_summary()}


@router.post("/{name}/run")
async def run_engine(
    name: str,
    payload: Dict[str, Any] = Body(default_factory=dict),
) -> Dict[str, Any]:
    try:
        engine = get_engine(name)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown engine '{name}'")
    try:
        result = engine(**payload)
    except TypeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc))
    return {"engine": name, "result": result}
