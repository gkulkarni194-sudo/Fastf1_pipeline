"""Runner for Monte Carlo simulation."""
from __future__ import annotations

from typing import Any, Callable

import numpy as np

from f1_pipeline.simulation.monte_carlo.sampler import MonteCarloSampler
from f1_pipeline.simulation.schemas import MonteCarloIteration, MonteCarloResult, MonteCarloSummary


class MonteCarloRunner:
    """Executes N iterations of a simulation with sampled parameters."""

    def __init__(self, config: dict[str, Any], layer3_params: dict[str, Any]):
        self.config = config.get("monte_carlo", {})
        self.iterations = int(self.config.get("iterations", 100))
        self.sampler = MonteCarloSampler(config, layer3_params)
        
    def run(self, base_seed: int, run_func: Callable[[dict[str, float], int], Any]) -> MonteCarloResult:
        """Run the simulation N times."""
        rng = np.random.default_rng(base_seed)
        
        iteration_results = []
        race_times = []
        all_lap_times = []
        
        for i in range(self.iterations):
            iter_seed = int(rng.integers(0, 2**31 - 1))
            sampled_params = self.sampler.sample(iter_seed)
            
            # Execute the deterministic simulation with these parameters
            result = run_func(sampled_params, iter_seed)
            
            if result.race_result:
                race_time = result.race_result.total_race_time
                lap_times = [l.lap_time for l in result.race_result.lap_results]
                
                race_times.append(race_time)
                all_lap_times.append(lap_times)
                
                iteration_results.append(MonteCarloIteration(
                    iteration=i,
                    seed=iter_seed,
                    sampled_parameters=sampled_params,
                    total_race_time=race_time,
                    lap_times=lap_times,
                    warnings=result.race_result.warnings
                ))
                
        # Calculate summary statistics
        if not race_times:
            raise RuntimeError("No successful Monte Carlo iterations completed.")
            
        race_times_arr = np.array(race_times)
        
        # Calculate per-lap statistics
        lap_times_arr = np.array(all_lap_times) # shape: (iterations, laps)
        mean_lap_times = np.mean(lap_times_arr, axis=0).tolist()
        std_lap_times = np.std(lap_times_arr, axis=0).tolist()
        
        summary = MonteCarloSummary(
            iterations=self.iterations,
            mean_race_time=float(np.mean(race_times_arr)),
            median_race_time=float(np.median(race_times_arr)),
            std_race_time=float(np.std(race_times_arr)),
            p05=float(np.percentile(race_times_arr, 5)),
            p25=float(np.percentile(race_times_arr, 25)),
            p50=float(np.percentile(race_times_arr, 50)),
            p75=float(np.percentile(race_times_arr, 75)),
            p95=float(np.percentile(race_times_arr, 95)),
            mean_lap_times=mean_lap_times,
            std_lap_times=std_lap_times,
        )
        
        return MonteCarloResult(summary=summary, iterations=iteration_results)
