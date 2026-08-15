"""Parameter sampling for Monte Carlo simulation."""
from __future__ import annotations

from typing import Any

import numpy as np


class MonteCarloSampler:
    """Samples parameters based on uncertainties from Layer 3 or config."""

    def __init__(self, config: dict[str, Any], layer3_params: dict[str, Any]):
        self.config = config.get("monte_carlo", {})
        self.distributions = self.config.get("distributions", {})
        self.layer3_params = layer3_params
        
    def sample(self, seed: int) -> dict[str, float]:
        """Draw a single sample of all uncertain parameters."""
        rng = np.random.default_rng(seed)
        sampled = dict(self.layer3_params) # Start with base values
        
        # In a full implementation, we'd look for standard_error in layer3_params
        # For now, we apply configured fractional standard deviations to the base values
        
        cda_base = self.layer3_params.get("effective_drag_parameter", 1.5)
        cda_std_frac = float(self.distributions.get("drag_parameter_stdev_fraction", 0.05))
        sampled["effective_drag_parameter"] = max(0.1, rng.normal(cda_base, cda_base * cda_std_frac))
        
        cla_base = self.layer3_params.get("effective_downforce_parameter", 4.0)
        cla_std_frac = float(self.distributions.get("downforce_parameter_stdev_fraction", 0.05))
        sampled["effective_downforce_parameter"] = max(0.1, rng.normal(cla_base, cla_base * cla_std_frac))
        
        # Pit loss uncertainty is absolute seconds, not fractional
        pit_loss_std = float(self.distributions.get("pit_loss_stdev_seconds", 0.5))
        sampled["_pit_loss_stdev"] = pit_loss_std
        
        return sampled
