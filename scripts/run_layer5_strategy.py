"""CLI script for running Layer 5 Strategy Optimization."""
import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to sys.path to allow running from scripts/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

def bootstrap_src_layout():
    """Ensure src/ is in sys.path for f1_pipeline imports."""
    src_dir = PROJECT_ROOT / "src"
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

bootstrap_src_layout()

from f1_pipeline.core.config import load_config
from f1_pipeline.core.logging import configure_logging
from f1_pipeline.core.paths import ProjectPaths, slugify_path_component
from f1_pipeline.simulation.scenario import Scenario
from f1_pipeline.strategy.optimizer import StrategyOptimizationPipeline

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Run Layer 5 Strategy Optimization.")
    parser.add_argument("--season", type=int, required=True, help="F1 Season (e.g., 2024)")
    parser.add_argument("--event", type=str, required=True, help="Event name (e.g., Bahrain)")
    parser.add_argument("--session", type=str, required=True, help="Session type (e.g., R)")
    parser.add_argument("--driver", type=str, required=True, help="Driver code (e.g., VER)")
    
    parser.add_argument("--algorithm", type=str, default="exhaustive", help="Optimization algorithm")
    parser.add_argument("--objective", type=str, default="race_time", help="Primary objective")
    
    parser.add_argument("--monte-carlo", action="store_true", help="Enable stochastic Monte Carlo optimization")
    parser.add_argument("--iterations", type=int, default=100, help="Number of MC iterations if enabled")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    
    parser.add_argument("--force", action="store_true", help="Force regeneration (ignore cache)")
    parser.add_argument("--pareto", action="store_true", help="Generate Pareto frontier")
    parser.add_argument("--sensitivity", action="store_true", help="Run sensitivity analysis on best strategy")
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    config = load_config()
    configure_logging(level=config.log_level, console=True)
    paths = ProjectPaths.from_root()
    
    logger.info("Initializing Layer 5 Strategy Optimization Pipeline...")
    
    event_slug = slugify_path_component(args.event)
    session_slug = slugify_path_component(args.session)
    driver = args.driver.upper()
    
    # In a real workflow, the base scenario would be dynamically constructed
    # from Layer 2/3 metadata (like total laps for that race).
    # Here we mock a base scenario to seed the search space.
    base_scenario = Scenario(
        season=args.season,
        event=args.event,
        session_type=args.session,
        driver_code=args.driver,
        total_laps=57,  # Assume 57 for Bahrain testing
        starting_fuel_kg=110.0
    )
    
    # 1. Fetch Layer 3 parameters
    physics_dir = paths.processed / "physics" / str(args.season) / event_slug / "q" / driver  # Mock using Q params for test
    if not physics_dir.exists():
        logger.error(f"Layer 3 physics parameters not found at {physics_dir}.")
        # Try finding ANY physics dir just to not fail if someone runs exact command but structure differs slightly
        import glob
        q_physics_dirs = glob.glob(str(paths.processed / "physics" / str(args.season) / "*" / "q" / driver))
        if q_physics_dirs:
            physics_dir = Path(q_physics_dirs[0])
            logger.info(f"Fallback: using found physics parameters from {physics_dir}")
        else:
            raise FileNotFoundError(f"Layer 3 physics parameters not found.")
            
    layer3_params = {}
    for param_file in ["aero_parameters.json", "cornering_parameters.json", "longitudinal_parameters.json", "tyre_parameters.json"]:
        file_path = physics_dir / param_file
        if file_path.exists():
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, dict) and "value" in v:
                            layer3_params[k] = v["value"]
                        else:
                            layer3_params[k] = v
                            
    # Override MC iterations in config if requested
    if args.monte_carlo:
        if "simulation" not in config.values:
            config.values["simulation"] = {}
        if "monte_carlo" not in config.values["simulation"]:
            config.values["simulation"]["monte_carlo"] = {}
        config.values["simulation"]["monte_carlo"]["iterations"] = args.iterations
        
    pipeline = StrategyOptimizationPipeline(config, paths)
    
    try:
        result = pipeline.execute(
            base_scenario=base_scenario,
            layer3_params=layer3_params,
            layer2_features={},
            algorithm=args.algorithm,
            objective=args.objective,
            monte_carlo=args.monte_carlo,
            seed=args.seed,
            force=args.force,
            pareto=args.pareto,
            sensitivity=args.sensitivity
        )
        
        logger.info(f"Optimization finished successfully.")
        logger.info(f"Evaluated strategies: {result.strategies_evaluated}")
        logger.info(f"Valid strategies: {result.strategies_valid}")
        logger.info(f"Best Strategy Score: {result.best_score}")
        if result.best_strategy:
            stops = len(result.best_strategy.pit_stops)
            seq = " -> ".join(s.compound for s in result.best_strategy.stints)
            logger.info(f"Best Strategy ({stops}-stop): {seq}")
            
    except Exception as e:
        logger.error(f"Pipeline execution failed", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
