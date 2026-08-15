#!/usr/bin/env python3
"""Run Layer 4 Simulation Pipeline.

Executes deterministic or Monte Carlo simulations using Layer 3 physics parameters,
Layer 2 features, and a specified scenario definition.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from _bootstrap import bootstrap_src_layout

bootstrap_src_layout()

from f1_pipeline.core.config import load_config
from f1_pipeline.core.logging import configure_logging
from f1_pipeline.core.paths import ProjectPaths, slugify_path_component
from f1_pipeline.simulation.pipeline import Layer4SimulationPipeline
from f1_pipeline.simulation.scenario import load_scenario

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Layer 4 Simulation Pipeline")
    parser.add_argument("--scenario", type=str, required=True, help="Path to scenario JSON file")
    parser.add_argument("--monte-carlo", action="store_true", help="Run Monte Carlo simulation")
    parser.add_argument("--iterations", type=int, help="Number of Monte Carlo iterations (overrides config)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic/MC execution")
    parser.add_argument("--force", action="store_true", help="Force execution even if identical run exists")
    parser.add_argument("--deterministic", action="store_true", help="Force deterministic mode (overrides config/args)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    
    config = load_config()
    configure_logging(level=config.log_level, console=True)
    paths = ProjectPaths.from_root()
    
    logger.info("Initializing Layer 4 Simulation Pipeline...")
    
    # Load scenario
    try:
        scenario = load_scenario(args.scenario)
        logger.info(f"Loaded scenario for {scenario.season} {scenario.event} {scenario.session_type} {scenario.driver_code}")
    except Exception as e:
        logger.error(f"Failed to load scenario: {e}")
        return 1
        
    # Determine mode
    run_mc = args.monte_carlo
    if args.deterministic:
        run_mc = False
    elif not args.monte_carlo and config.values.get("simulation", {}).get("default_mode") == "monte_carlo":
        run_mc = True
        
    # Override iterations if requested
    if args.iterations and "monte_carlo" in config.values.get("simulation", {}):
        config.values["simulation"]["monte_carlo"]["iterations"] = args.iterations

    pipeline = Layer4SimulationPipeline(config=config, paths=paths)
    
    try:
        # In a real system, we'd check if an identical run exists based on
        # scenario_hash and layer3 output hashes, and skip if not --force.
        # But we'll always run for now per typical pipeline behavior.
        
        result = pipeline.execute(
            scenario=scenario,
            run_monte_carlo=run_mc,
            seed=args.seed,
            force=args.force
        )
        
        if result.success:
            logger.info("Simulation completed successfully.")
            if result.mode == "deterministic" and result.race_result:
                logger.info(f"Total Race Time: {result.race_result.total_race_time:.3f}s")
                logger.info(f"Total Fuel Used: {result.race_result.total_fuel_used:.2f}kg")
                logger.info(f"Warnings: {len(result.race_result.warnings)}")
            elif result.mode == "monte_carlo" and result.monte_carlo_result:
                logger.info(f"Mean Race Time: {result.monte_carlo_result.summary.mean_race_time:.3f}s")
                logger.info(f"p05-p95 Range: [{result.monte_carlo_result.summary.p05:.3f}s, {result.monte_carlo_result.summary.p95:.3f}s]")
            return 0
        else:
            logger.error(f"Simulation failed: {result.message}")
            return 1
            
    except Exception as e:
        logger.exception("Pipeline execution failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
