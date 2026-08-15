"""Deterministic hashing of Strategy objects."""
from __future__ import annotations

import hashlib
import json

from f1_pipeline.strategy.schemas import Strategy


def hash_strategy(strategy: Strategy) -> str:
    """Generate a deterministic hash for a Strategy object.
    
    The hash must be independent of dictionary ordering.
    """
    data = strategy.model_dump(mode="json")
    
    # Sort the json keys and serialize without whitespace
    json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
    
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()
