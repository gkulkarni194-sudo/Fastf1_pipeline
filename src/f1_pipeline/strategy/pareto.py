"""Pareto optimization."""
from __future__ import annotations

import pandas as pd


def identify_pareto_frontier(df: pd.DataFrame, minimize_metrics: list[str]) -> pd.DataFrame:
    """Identify the Pareto frontier for a set of strategies.
    
    Args:
        df: DataFrame containing the strategies and metrics.
        minimize_metrics: List of column names to minimize.
        
    Returns:
        DataFrame with an additional boolean column 'is_pareto_optimal'.
    """
    if df.empty or not minimize_metrics:
        df["is_pareto_optimal"] = False
        return df
        
    # Only consider valid strategies for the frontier
    valid_mask = df.get("is_valid", df["constraint_status"] == "valid")
    
    is_pareto = []
    
    for i in range(len(df)):
        if not valid_mask.iloc[i]:
            is_pareto.append(False)
            continue
            
        row = df.iloc[i]
        optimal = True
        
        # Check if any other valid row dominates this row
        for j in range(len(df)):
            if i == j or not valid_mask.iloc[j]:
                continue
                
            other_row = df.iloc[j]
            
            # A row dominates if it is better or equal in ALL metrics, and strictly better in AT LEAST ONE
            better_or_equal_all = True
            strictly_better_any = False
            
            for metric in minimize_metrics:
                # Handle NaNs
                val = row[metric]
                other_val = other_row[metric]
                
                if pd.isna(val) or pd.isna(other_val):
                    better_or_equal_all = False
                    break
                    
                if other_val > val:
                    better_or_equal_all = False
                    break
                elif other_val < val:
                    strictly_better_any = True
                    
            if better_or_equal_all and strictly_better_any:
                optimal = False
                break
                
        is_pareto.append(optimal)
        
    df = df.copy()
    df["is_pareto_optimal"] = is_pareto
    return df
