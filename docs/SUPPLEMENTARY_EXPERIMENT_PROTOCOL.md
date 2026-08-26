# Frozen Supplementary Experiment Protocol

Protocol timestamp: 2026-08-27, before running the supplementary retrieval,
behaviour, or test-generation analyses described below.

## Status and scope

The official QASPER test split has already been used for the primary frozen
retrieval evaluation. All analyses in this document are therefore labelled
**supplementary**. They will not be used to modify ControllerV3, choose a more
favourable overlap threshold, or replace the primary ControllerV3 versus BM25
top-7 comparison.

Frozen artifacts:

- ControllerV3 source SHA-256:
  `96d5d3391b4372816507138e9013870df4b22e2328019e1111b009be91949166`
- ControllerV3 test output SHA-256:
  `a33831239f9ea0e5d9e562d139e65b99b5d6217dcabf9579edda131bc2af9355`
- no-section output SHA-256:
  `7e01e0ca3b584332abe5b219c4f0579ff8cdf570e6c70ddb2d143dde31b2208b`
- BM25 top-7 output SHA-256:
  `09e62573bb91f5a0a711add0f9d168e9a6a0d783ec92f31d54cc9ab15b3d9973`
- BM25 top-8 output SHA-256:
  `c2ad0ce014d144af799582d10c7daf6a677436eaea07e8ca574743079150ee52`

ControllerV3 will remain a rule-based, question-aware variable-budget
controller. No evidence-sufficiency-based dynamic stopping will be introduced.

## S1: Retrieval reference points

Two reference methods pre-specified in the interim report will be added:

- **Abstract-only:** return every abstract evidence unit for the paper and no
  other evidence.
- **Read-all:** return every retrievable abstract, body chunk, table, figure
  caption, and residual figure/table unit.

They are descriptive low- and high-cost reference points. Read-all will not be
used for local answer generation.

## S2: Budget-matched section-expansion controls

The existing full-versus-no-section ablation changes both targeting and cost.
Two gold-independent controls will isolate these factors.

### Generic count-matched expansion

For each question:

1. start with the frozen no-section evidence order; if it already exceeds the
   full controller's target count, retain its first target-count units;
2. set the target unit count to the frozen full ControllerV3 count;
3. rank all retrievable paper units with the original question using BM25;
4. add the highest-ranked unselected units until the target count is reached.

This exactly matches the full controller's question-specific unit-count
schedule but replaces section-aware additions with generic BM25 additions.

### Generic token-matched expansion

For each question:

1. start with the frozen no-section evidence order; if removing trailing units
   reduces absolute distance to the full controller's word target, remove them
   before generic expansion;
2. set the target word count to the frozen full ControllerV3 retrieved words;
3. consider unselected units in generic BM25 rank order;
4. add a unit while it reduces the absolute distance to the target, stopping
   once the next ranked unit would not improve the match.

This is a sensitivity control for evidence-length differences. Residual token
and unit-count differences will be reported rather than assumed away.

Primary supplementary mechanism contrast:

- ControllerV3 minus generic count-matched expansion.

Sensitivity contrast:

- ControllerV3 minus generic token-matched expansion.

Metrics use the already defined threshold 0.5: Evidence Recall, Question Hit
Rate, Average Best Overlap, retrieved units, estimated tokens, and Recall per
1,000 estimated tokens. Uncertainty uses 5,000 paper-level paired percentile
bootstrap samples with seed 42. Thresholds 0.3 and 0.7 will not be searched for
the mechanism conclusion.

## S3: Variable-budget and controller-behaviour analysis

The following descriptive quantities will be computed before inspecting any
decision-path subgroup results:

- mean, standard deviation, median, IQR, P10, and P90 of retrieved units,
  evidence words, and estimated tokens;
- paired per-question ControllerV3 minus top-7 token differences;
- proportions for which ControllerV3 uses fewer, equal, or more estimated
  tokens than top-7;
- mutually exclusive controller paths, following implementation order:
  definition; result/data; method/complex; default;
- per-path question count, gold-question count, Evidence Recall, Question Hit
  Rate, Average Best Overlap, and average/median estimated tokens;
- action frequencies, action sequence frequencies, and units added by action.

Because these subgroup analyses were fixed after the primary test result was
known, they are exploratory/descriptive. They will not be presented as new
confirmatory tests.

## S4: Cluster-sampled downstream answer generation

### Sampling

- Source: the complete official QASPER test split.
- Sort papers by paper ID, then shuffle papers with Python's `random.Random(42)`.
- Select whole papers in that order until their cumulative question count is at
  least 200; include every question from the final selected paper.
- Save the selected paper and question IDs before building or inspecting
  generated answers.

### Methods

- ControllerV3;
- BM25 top-7, the primary cost-matched baseline;
- BM25 top-8, the adjacent higher-cost fixed baseline;
- ControllerV3 without section-aware expansion.

### Prompt and model

- Model: `qwen2.5:3b` served locally by Ollama;
- identical prompt template and evidence ordering for every method;
- `temperature=0`, `seed=42`, `num_ctx=8192`, `num_predict=256`;
- no 6,000-character cap;
- an explicit evidence limit of 20,000 characters as a safety bound; no selected
  method is expected to reach the model context window under the observed
  retrieval budgets;
- save retained evidence units/chars and Ollama `prompt_eval_count`;
- hash every complete prompt and call the model once per unique prompt;
- reuse that generation for every method-question record with the same hash.

The final point is mandatory: repeated inference on identical prompts must not
create apparent method differences through local runtime nondeterminism.

### Execution gate

Run a 20-question smoke sample first. The smoke run may be used only to verify
schema, prompt-hash reuse, context length, output parsing, and completion. It
must not be used to revise ControllerV3 or choose questions. After the smoke
audit passes, run the frozen cluster sample without changing the protocol.

Protocol amendment before the frozen sample: the first completion-check smoke
used `num_predict=128` and produced two length-stop records among 67 unique
prompts; one answer was visibly incomplete. Because completion checking is an
explicit execution-gate purpose above, `num_predict` was increased to 256 and
the full 20-question smoke was rerun from a new output file. The sample, prompt
template, evidence, model, seed, and ControllerV3 were unchanged. Only the
256-token smoke is used to decide whether the frozen sample may proceed; both
smoke audits are retained for provenance.

### Generation outcomes

- official-style normalized Answer F1 and Exact Match;
- Answer F1 by best-matching reference answer type: extractive, abstractive,
  boolean, and unanswerable/none;
- unanswerable accuracy;
- successful generations and missing/error records;
- actual average/total prompt and output tokens;
- unique prompt count and prompt-reuse rate.

Primary generation contrast:

- ControllerV3 minus BM25 top-7 Answer F1.

Secondary planned contrasts:

- ControllerV3 minus BM25 top-8;
- ControllerV3 minus no-section.

Each difference will receive a 95% interval from 5,000 paired paper-cluster
bootstrap samples with seed 42. The report will lead with effect sizes and
intervals. It will not infer equivalence from a non-significant or
zero-crossing interval.

## Artifact and Git policy

Supplementary artifacts are written under `outputs/supplementary/`. Source,
protocols, small CSV/JSON summaries, audits, figures, and SHA-256 manifests are
committed to Git after each major stage. Rebuildable QASPER test data, local
models, virtual environments, and large per-question JSONL outputs remain
local and ignored by Git.
