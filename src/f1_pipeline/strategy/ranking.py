"""Strategy ranking."""
from __future__ import annotations

import pandas as pd

from f1_pipeline.strategy.schemas import StrategyEvaluation


def rank_strategies(evaluations: list[StrategyEvaluation]) -> pd.DataFrame:
    """Rank evaluated strategies by their objective score.
    
    Invalid strategies are placed at the bottom.
    Returns a DataFrame sorted by rank.
    """
    records = []
    
    for eval_data in evaluations:
        records.append({
            "strategy_hash": eval_data.strategy_hash,
            "strategy_json": eval_data.strategy.model_dump_json(),
            "constraint_status": eval_data.constraint_status,
            "objective_score": eval_data.objective_score,
            "race_time": eval_data.race_time,
            "mean_race_time": eval_data.mean_race_time,
            "std_race_time": eval_data.std_race_time,
            "p05_race_time": eval_data.p05_race_time,
            "p50_race_time": eval_data.p50_race_time,
            "p95_race_time": eval_data.p95_race_time,
            "pit_stops": len(eval_data.strategy.pit_stops),
        })
        
    df = pd.DataFrame(records)
    if df.empty:
        return df
        
    # Sort by valid status first, then by objective score ascending
    # Invalid strategies (score NaN) will naturally fall to the bottom if we handle NA
    df["is_valid"] = df["constraint_status"] == "valid"
    
    df = df.sort_values(
        by=["is_valid", "objective_score"],
        ascending=[False, True],
        na_position="last"
    )
    
    # Assign ranks
    df["rank"] = range(1, len(df) + 1)
    
    return df
