"""API Routes package."""
from fastapi import APIRouter

from .experiments import router as experiments_router
from .health import router as health_router
from .metadata import router as metadata_router
from .optimizations import router as optimizations_router
from .physics import router as physics_router
from .simulations import router as simulations_router
from .strategies import router as strategies_router

router = APIRouter()

router.include_router(health_router, prefix="/health", tags=["Health"])
router.include_router(metadata_router, tags=["Metadata"])
router.include_router(physics_router, prefix="/physics", tags=["Physics"])
router.include_router(simulations_router, prefix="/simulations", tags=["Simulations"])
router.include_router(optimizations_router, prefix="/optimizations", tags=["Optimizations"])
router.include_router(strategies_router, prefix="/strategies", tags=["Strategies"])
router.include_router(experiments_router, prefix="/experiments", tags=["Experiments"])
