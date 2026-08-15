"""Pit lap combination generator."""
from __future__ import annotations

import itertools
from typing import Iterator


def generate_pit_lap_combinations(
    total_laps: int,
    num_stops: int,
    min_stint_laps: int,
    pit_window_min: int | None = None,
    pit_window_max: int | None = None
) -> Iterator[tuple[int, ...]]:
    """Generate valid pit lap combinations for a given number of stops.
    
    Args:
        total_laps: Total number of laps in the race.
        num_stops: Number of pit stops.
        min_stint_laps: Minimum allowed laps for any stint.
        pit_window_min: Optional earliest allowed lap for a pit stop.
        pit_window_max: Optional latest allowed lap for a pit stop.
        
    Yields:
        Tuples representing the lap number of each pit stop.
        For example, a 2-stop strategy might yield (20, 40).
    """
    if num_stops == 0:
        yield ()
        return

    # Determine allowable pit lap range
    start_lap = max(min_stint_laps, pit_window_min) if pit_window_min else min_stint_laps
    end_lap = min(total_laps - min_stint_laps, pit_window_max) if pit_window_max else (total_laps - min_stint_laps)
    
    if start_lap > end_lap:
        return
        
    # Generate combinations
    for combo in itertools.combinations(range(start_lap, end_lap + 1), num_stops):
        # Enforce min_stint_laps between stops
        valid = True
        for i in range(len(combo) - 1):
            if combo[i+1] - combo[i] < min_stint_laps:
                valid = False
                break
                
        if valid:
            yield combo
