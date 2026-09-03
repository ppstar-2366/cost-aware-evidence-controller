# Question-Aware Variable-Budget Evidence Selection for Scientific QA

This repository contains the implementation and experiment records for Ruotong
Peng's MSc individual project in Computing (Artificial Intelligence and Machine
Learning) at Imperial College London.

The project studies evidence selection when a scientific paper is already
known. Its main question is whether a lightweight controller can allocate
different evidence budgets to different questions and obtain a better
retrieval-quality/context-cost trade-off than fixed-depth BM25.

## Method scope

QASPER papers are converted into typed evidence units: abstracts, overlapping
body chunks, table descriptions, figure captions, and residual figure/table
text. BM25 supplies the base ranking. ControllerV3 starts from a small global
result set and applies bounded expansions according to lexical cues in the
question and the paper's section or figure/table structure.

The controller is deterministic and does not call a language model during
evidence selection. It is a question-aware, rule-based budget allocator. It
does **not** inspect the selected evidence to estimate sufficiency, and the
Stop action marks the end of a rule branch rather than evidence-conditioned
dynamic stopping.

The initial Validation50 experiments informed the rules and are retained only
as development history. ControllerV3 was then frozen and evaluated once on the
complete official QASPER test split.

## Main results

The primary retrieval evaluation covers 416 papers and 1,451 questions. At the
pre-specified evidence-overlap threshold of 0.5:

| Method | Evidence Recall | Question Hit Rate | Mean estimated tokens |
| --- | ---: | ---: | ---: |
| BM25 top-5 | 0.6149 | 0.8003 | 1,171 |
| BM25 top-7 | 0.7059 | 0.8624 | 1,629 |
| BM25 top-8 | 0.7442 | 0.8876 | 1,864 |
| BM25 top-10 | 0.8084 | 0.9127 | 2,305 |
| ControllerV3 | 0.7099 | 0.8706 | 1,638 |
| ControllerV3 without section expansion | 0.6879 | 0.8558 | 1,534 |

ControllerV3 minus BM25 top-7 has an Evidence Recall difference of +0.0040
(95% paper-level paired bootstrap interval [-0.0118, +0.0184]) and a Question
Hit Rate difference of +0.0081 ([-0.0044, +0.0210]). Their aggregate quality
and mean estimated cost are therefore close in this evaluation, but the
intervals do not establish either superiority or formal equivalence.

Question-level budget matching further separates the effect of added context
from the effect of section targeting. Relative to generic BM25 additions with
the same per-question unit count, ControllerV3's Evidence Recall difference is
+0.0027 ([-0.0060, +0.0110]). The corresponding token-matched difference is
+0.0035 ([-0.0051, +0.0118]). These results do not show a clear independent
aggregate benefit from section-aware additions at a matched budget.

A frozen downstream sample contains 53 complete paper clusters and 201
questions. With the same local Qwen2.5-3B generator, ControllerV3 and BM25
top-7 obtain Answer F1 scores of 0.3280 and 0.3278. Their paired difference is
+0.0002 ([-0.0313, +0.0312]). This result is specific to the sampled papers,
prompt, and generator; it is not a full-test generation result.

Detailed protocols and interpretation boundaries are in:

- [Frozen test protocol](docs/TEST_EVALUATION_PROTOCOL.md)
- [Frozen test results](docs/TEST416_RESULTS.md)
- [Supplementary experiment protocol](docs/SUPPLEMENTARY_EXPERIMENT_PROTOCOL.md)
- [Supplementary retrieval results](docs/SUPPLEMENTARY_RETRIEVAL_RESULTS.md)
- [Frozen generation results](docs/TEST_GENERATION_RESULTS.md)

## Repository layout

~~~text
src/                  experiment implementation and audit scripts
data/processed/       development subsets; the rebuilt test file is ignored
outputs/test416/      test summaries, intervals, error analysis, and manifests
outputs/supplementary/  budget-matched, behaviour, and generation summaries
outputs/figures/      result figures and provenance metadata
docs/                 protocols, results, data dictionary, and reproduction notes
~~~

The core entry points are:

- src/build_evidence_units.py: construct typed evidence units from QASPER;
- src/run_retrieval_experiment.py: run fixed BM25 and ControllerV3 retrieval;
- src/bootstrap_retrieval.py: compute paper-level bootstrap intervals;
- src/run_supplementary_retrieval.py: run reference and budget-matched controls;
- src/analyze_controller_behavior.py: summarise question-level budgets and actions;
- src/build_test_generation_sample.py: freeze the paper-cluster generation sample;
- src/run_deduplicated_ollama_generation.py: run one local inference per unique prompt;
- src/evaluate_test_generation.py: score answers and bootstrap paired differences;
- the audit scripts check alignment, completeness, and hashes.

## Environment

Create a virtual environment and install the recorded dependencies:

~~~bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
~~~

The answer-generation stage additionally requires Ollama and the
qwen2.5:3b model. Retrieval and statistical analyses do not require Ollama.
Windows equivalents and the full command sequence are documented in the
[reproduction guide](docs/REPRODUCTION_GUIDE_ZH.md).

When the ignored raw test outputs are present, the main audits can be run with:

~~~bash
.venv/bin/python src/audit_test_experiment.py
.venv/bin/python src/audit_supplementary.py
.venv/bin/python src/audit_test_generation.py
~~~

## Data and artifact availability

QASPER is loaded from allenai/qasper at revision
13b496d2a5359329b110e3419628de3cf791843b. The complete processed test file,
local model files, prompts, generations, and large per-question retrieval JSONL
files are not committed. Their SHA-256 hashes and sizes are recorded in the
manifests under outputs/test416/ and outputs/supplementary/.

Committed artifacts include the result tables, paired intervals, question-level
diagnostics, integrity audits, and figure provenance needed to check the claims
reported above. The dissertation source is maintained separately in Overleaf
and is not part of this experiment repository.

## Limitations

- Evidence coverage is a project-specific lexical-overlap measure, not a direct
  measure of semantic sufficiency.
- Estimated evidence tokens are computed as words multiplied by 1.3; only the
  generation experiment records actual Ollama prompt-token counts.
- ControllerV3 inherits the limitations of BM25 ranking, hand-written lexical
  rules, overlapping text chunks, and caption-only figure/table handling.
- The downstream evaluation uses one quantised 3B generator and a frozen
  201-question sample.
- Test-set diagnostics are supplementary. A method revised from those
  diagnostics would require a new independent evaluation set.

## Author

Ruotong Peng
