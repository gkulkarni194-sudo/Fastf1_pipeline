"""Position objective."""
from __future__ import annotations

from f1_pipeline.strategy.schemas import StrategyEvaluation


class PositionObjective:
    """Stub for expected finishing position objective."""
    
    def score(self, evaluation: StrategyEvaluation) -> float | None:
        # Expected position would require modeling opponents.
        # This is out of scope for the current layer implementation, but
        # provides a clean extension point.
        raise NotImplementedError("PositionObjective requires opponent modeling.")
