"""Constraint validation for strategy candidates."""
from __future__ import annotations

from f1_pipeline.strategy.schemas import ConstraintResult, Strategy
from f1_pipeline.strategy.search_space import SearchSpace


def evaluate_static_constraints(strategy: Strategy, space: SearchSpace) -> ConstraintResult:
    """Evaluate constraints that do not require simulation."""
    violations = []
    
    # 1. Total laps matching
    if not strategy.stints:
        violations.append("Strategy has no stints")
        return ConstraintResult(valid=False, violations=violations)
        
    last_lap = strategy.stints[-1].end_lap
    if last_lap != space.total_laps:
        violations.append(f"Strategy covers {last_lap} laps, expected {space.total_laps}")
        
    # 2. Minimum stint length
    for i, stint in enumerate(strategy.stints):
        stint_len = stint.end_lap - stint.start_lap + 1
        if stint_len < space.stint_min_laps:
            violations.append(f"Stint {i+1} length ({stint_len}) < min ({space.stint_min_laps})")
            
    # 3. Two-compound rule (if multiple compounds available)
    if len(space.compounds) > 1:
        compounds_used = {stint.compound for stint in strategy.stints}
        if len(compounds_used) < 2:
            violations.append(f"F1 regulations require using at least two different compounds. Used: {compounds_used}")
            
    # 4. Number of stops
    num_stops = len(strategy.pit_stops)
    if num_stops < space.stops.min or num_stops > space.stops.max:
        violations.append(f"Stops ({num_stops}) out of bounds [{space.stops.min}, {space.stops.max}]")
        
    # 5. Compound availability
    for stint in strategy.stints:
        if stint.compound not in space.compounds:
            violations.append(f"Compound {stint.compound} not in available list: {space.compounds}")
            
    return ConstraintResult(
        valid=len(violations) == 0,
        violations=violations
    )


def evaluate_dynamic_constraints(result: "SimulationResult", config: dict) -> ConstraintResult:
    """Evaluate constraints based on the Layer 4 simulation outcome."""
    violations = []
    
    # Example constraints (could be configurable)
    
    # 1. Successful simulation
    if not result.success:
        violations.append(f"Simulation failed: {result.message}")
        return ConstraintResult(valid=False, violations=violations)
        
    # 2. Fuel feasibility (if ran out of fuel)
    # The simulation engine will usually halt and flag success=False, or we can check race_result
    if result.race_result and result.race_result.warnings:
        for w in result.race_result.warnings:
            if "fuel" in w.lower():
                violations.append(f"Fuel constraint warning: {w}")
                
    # 3. Tyre cliff (don't allow exceeding absolute max tyre age config)
    # The Simulation Result holds stints
    if result.race_result:
        for stint in result.race_result.stint_results:
            # We assume a hard max age around 80 from Layer 4 config
            if stint.tyre_age_end > 80:
                violations.append(f"Tyre age {stint.tyre_age_end} exceeded maximum hard limit 80.")
                
    return ConstraintResult(
        valid=len(violations) == 0,
        violations=violations
    )
