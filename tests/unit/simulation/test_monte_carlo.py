from __future__ import annotations

from f1_pipeline.simulation.monte_carlo.runner import MonteCarloRunner
from f1_pipeline.simulation.monte_carlo.sampler import MonteCarloSampler
from f1_pipeline.simulation.schemas import MonteCarloResult, RaceResult, SimulationResult


def test_monte_carlo_sampler():
    config = {
        "monte_carlo": {
            "distributions": {
                "drag_parameter_stdev_fraction": 0.1,
                "pit_loss_stdev_seconds": 1.0
            }
        }
    }
    layer3_params = {"effective_drag_parameter": 1.5, "effective_downforce_parameter": 4.0}
    
    sampler = MonteCarloSampler(config, layer3_params)
    
    # Same seed should produce same sample
    sample1 = sampler.sample(42)
    sample2 = sampler.sample(42)
    assert sample1 == sample2
    
    # Different seed should produce different sample
    sample3 = sampler.sample(43)
    assert sample1 != sample3
    
    # Base parameter with 0 stdev config should remain constant
    # Wait, the sampler currently uses 0.05 default if not specified in config
    assert "_pit_loss_stdev" in sample1
    assert sample1["_pit_loss_stdev"] == 1.0


def test_monte_carlo_runner():
    config = {
        "monte_carlo": {
            "iterations": 10,
            "distributions": {}
        }
    }
    layer3_params = {"effective_drag_parameter": 1.5}
    
    # Mock run function
    def mock_run(params: dict[str, float], seed: int) -> SimulationResult:
        # Just return a fake race result where time depends on seed
        drag = params.get("effective_drag_parameter", 1.5)
        
        from f1_pipeline.simulation.schemas import LapResult
        
        race_time = 5000.0 + (drag * 100.0) + (seed % 100)
        
        lap_result = LapResult(
            lap_number=1, lap_time=race_time, elapsed_time=race_time,
            fuel_used=1.0, fuel_remaining=99.0, tyre_age=1,
            tyre_compound="SOFT", tyre_grip=1.0, vehicle_mass=800.0
        )
        
        race_result = RaceResult(
            total_race_time=race_time,
            total_laps=1,
            lap_results=[lap_result],
            stint_results=[],
            pit_events=[],
            total_fuel_used=1.0,
            total_pit_time=0.0
        )
        
        return SimulationResult(success=True, race_result=race_result)
        
    runner = MonteCarloRunner(config, layer3_params)
    result = runner.run(base_seed=123, run_func=mock_run)
    
    assert result.summary.iterations == 10
    assert len(result.iterations) == 10
    assert result.summary.mean_race_time > 0
    assert result.summary.p95 >= result.summary.p05
