"""Full race strategy generator."""
from __future__ import annotations

import logging
from typing import Iterator

from f1_pipeline.strategy.generators.pit_windows import generate_pit_lap_combinations
from f1_pipeline.strategy.generators.tyre_strategies import generate_compound_sequences
from f1_pipeline.strategy.schemas import PitSpec, StintSpec, Strategy
from f1_pipeline.strategy.search_space import SearchSpace

logger = logging.getLogger(__name__)


class RaceStrategyGenerator:
    """Generates complete valid Strategy candidates from a search space."""
    
    def __init__(self, search_space: SearchSpace, default_pit_loss_seconds: float = 22.0):
        self.space = search_space
        self.default_pit_loss = default_pit_loss_seconds
        
    def generate(self) -> Iterator[Strategy]:
        """Generate all candidate strategies."""
        pw_min = self.space.pit_windows.min_lap if self.space.pit_windows else None
        pw_max = self.space.pit_windows.max_lap if self.space.pit_windows else None
        
        for num_stops in range(self.space.stops.min, self.space.stops.max + 1):
            
            compound_sequences = list(generate_compound_sequences(
                available_compounds=self.space.compounds,
                num_stops=num_stops
            ))
            
            pit_combinations = generate_pit_lap_combinations(
                total_laps=self.space.total_laps,
                num_stops=num_stops,
                min_stint_laps=self.space.stint_min_laps,
                pit_window_min=pw_min,
                pit_window_max=pw_max
            )
            
            # Cartesian product of valid compound sequences and valid pit laps
            for pit_laps in pit_combinations:
                for compounds in compound_sequences:
                    yield self._build_strategy(compounds, pit_laps)
                    
    def _build_strategy(self, compounds: tuple[str, ...], pit_laps: tuple[int, ...]) -> Strategy:
        """Construct a Strategy object from sequences."""
        stints = []
        pit_stops = []
        
        current_lap = 1
        
        # Build stints up to the final pit stop
        for i, pit_lap in enumerate(pit_laps):
            stints.append(StintSpec(
                compound=compounds[i],
                start_lap=current_lap,
                end_lap=pit_lap
            ))
            pit_stops.append(PitSpec(
                lap=pit_lap,
                pit_loss_seconds=self.default_pit_loss,
                change_compound_to=compounds[i+1]
            ))
            current_lap = pit_lap + 1
            
        # Final stint
        stints.append(StintSpec(
            compound=compounds[-1],
            start_lap=current_lap,
            end_lap=self.space.total_laps
        ))
        
        return Strategy(
            driver_code=self.space.driver_code,
            stints=stints,
            pit_stops=pit_stops
        )
