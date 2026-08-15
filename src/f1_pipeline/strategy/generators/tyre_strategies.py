"""Tyre compound sequence generator."""
from __future__ import annotations

import itertools
from typing import Iterator


def generate_compound_sequences(
    available_compounds: list[str],
    num_stops: int,
    mandatory_compounds: list[str] | None = None
) -> Iterator[tuple[str, ...]]:
    """Generate all possible compound sequences for a given number of stops.
    
    Args:
        available_compounds: List of compounds available (e.g. ["SOFT", "MEDIUM", "HARD"])
        num_stops: Number of pit stops (so num_stops + 1 stints)
        mandatory_compounds: Optional list of compounds that MUST appear in the sequence.
        
    Yields:
        Tuples representing the compound used in each stint.
    """
    num_stints = num_stops + 1
    
    # Generate all permutations (with replacement) of compounds for the number of stints
    for sequence in itertools.product(available_compounds, repeat=num_stints):
        
        # Check mandatory compounds
        if mandatory_compounds:
            valid = True
            for mc in mandatory_compounds:
                if mc not in sequence:
                    valid = False
                    break
            if not valid:
                continue
                
        # Some rules might say we must use at least two DIFFERENT compounds.
        # By default F1 rules require using 2 different compounds in a dry race.
        # We will enforce this if we have more than 1 compound available.
        if len(available_compounds) > 1 and len(set(sequence)) < 2:
            continue
            
        yield sequence
