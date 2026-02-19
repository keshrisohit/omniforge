# TASK-009: Implement A/B Testing and Experiment Manager

## Objective

Create the experiment manager for A/B testing prompt variations including traffic allocation and statistical analysis.

## Requirements

### Experiment Manager (`src/omniforge/prompts/experiments/manager.py`)

**ExperimentManager class**:

Constructor:
- `repository: PromptRepository`

Methods:

`async create_experiment(prompt_id, name, description, success_metric, variants, created_by) -> PromptExperiment`:
- Validate prompt exists
- Validate variants sum to 100%
- Create experiment in DRAFT status
- Return created experiment

`async start_experiment(experiment_id: str) -> PromptExperiment`:
- Verify experiment is in DRAFT or PAUSED status
- Check no other RUNNING experiment exists for this prompt
- Set status to RUNNING, record start_date
- Return updated experiment

`async stop_experiment(experiment_id: str) -> PromptExperiment`:
- Set status to PAUSED
- Return updated experiment

`async complete_experiment(experiment_id: str, results: dict) -> PromptExperiment`:
- Set status to COMPLETED, record end_date
- Store statistical results
- Return updated experiment

`async select_variant(prompts: dict, tenant_id: str) -> Optional[VariantSelection]`:
- Check for active experiment on any prompt in the dict
- If active, allocate user to variant based on traffic percentages
- Use deterministic assignment (hash of tenant_id + experiment_id)
- Return selected variant info or None

`async promote_variant(experiment_id: str, variant_id: str, promoted_by: str) -> Prompt`:
- Set variant's prompt version as current
- Complete experiment
- Return updated prompt

### Traffic Allocation (`src/omniforge/prompts/experiments/allocation.py`)

**TrafficAllocator class**:
- `allocate(experiment: PromptExperiment, identifier: str) -> str`:
  - Hash identifier to get consistent assignment
  - Map hash to traffic percentages
  - Return variant_id

### Statistical Analysis (`src/omniforge/prompts/experiments/analysis.py`)

**ExperimentAnalyzer class**:
- `analyze(experiment: PromptExperiment, metrics: dict) -> AnalysisResult`:
  - Calculate basic statistics per variant
  - Compute statistical significance (p-value)
  - Determine if sample size is sufficient
  - Return analysis with recommendations

**AnalysisResult dataclass**:
- variant_stats: dict of per-variant statistics
- winner: Optional variant_id
- is_significant: bool
- confidence_level: float
- sample_size_sufficient: bool

### Package Init
- `src/omniforge/prompts/experiments/__init__.py`

## Acceptance Criteria
- [ ] Experiments can be created, started, stopped, completed
- [ ] Only one RUNNING experiment per prompt
- [ ] Traffic allocation is deterministic and consistent
- [ ] Variant selection respects traffic percentages
- [ ] Statistical analysis computes basic significance
- [ ] Promote updates prompt to winning version
- [ ] Unit tests cover experiment lifecycle
- [ ] Tests verify traffic distribution is approximately correct

## Dependencies
- TASK-001 (models, errors)
- TASK-002 (repository)

## Estimated Complexity
Complex
