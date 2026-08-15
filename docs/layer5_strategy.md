# Layer 5: Strategy Optimization

Layer 5 answers the question: **"What strategy performs best under the defined objective and constraints?"**

It strictly uses the **Layer 4 Simulation Engine** to evaluate candidates, preventing any duplication of physics logic or vehicle dynamic calculations.

## Responsibilities
- **Search Space Generation**: Building combinatorial spaces of pit stops, tyre compounds, and stint bounds.
- **Candidate Validation**: Filtering invalid strategies via static constraints (e.g. F1's two-compound rule).
- **Simulation Wrapping**: Wrapping Strategy objects into Simulation Scenarios to invoke Layer 4.
- **Objective Evaluation**: Scoring simulated strategies based on configurable objectives (Race Time, Robustness, Composite).
- **Analysis**: Producing Pareto frontiers and sensitivity bounds for the selected optimum.

## Algorithms
Currently supports:
- **Exhaustive Optimization**: Complete enumeration of the search space. Excellent for deterministic configurations with hard pit-window bounds.
- *Bayesian Optimization (Stub)*: Designed for expansion into continuous variables (e.g. fuel burn optimization, delta targeting).

## Usage
To run the optimization engine from the command line:

```bash
python scripts/run_layer5_strategy.py --season 2024 --event Bahrain --session R --driver VER --algorithm exhaustive --objective race_time --pareto --seed 42
```

To run with uncertainty/risk evaluated via Monte Carlo:
```bash
python scripts/run_layer5_strategy.py ... --monte-carlo --iterations 100 --objective composite
```

## Schema & Persistence
Optimizations are persisted via `strategy_runs`, and detailed analyses (ranked dataframes, sensitivity) are saved to Parquet and registered in `strategy_assets`. Best strategy definitions are saved as JSON.

## Limitations
- Exhaustive search can combinatorially explode if `max_stops` > 4 or if `pit_window` bounds are completely unrestricted. Rely on configuration defaults to bound the space.
- Does not model traffic or opponent interaction natively (this belongs to position-based objectives paired with an opponent model).
