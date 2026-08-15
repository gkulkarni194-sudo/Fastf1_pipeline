"""Strategy analysis endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends

from f1_pipeline.api.schemas.strategies import StrategyCompareRequest, StrategyCompareResponse

router = APIRouter()


@router.post("/compare", response_model=StrategyCompareResponse)
async def compare_strategies(request: StrategyCompareRequest):
    """Compare multiple strategy definitions side-by-side."""
    # Stub implementation
    return StrategyCompareResponse(comparisons=[])
