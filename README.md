# Question-Aware Variable-Budget Evidence Selection for Scientific Paper QA

This repository contains the code and experiment outputs from my MSc Computing
(Artificial Intelligence and Machine Learning) individual project at Imperial
College London. The project asks a fairly specific question: when the target
paper is already known, can the amount of evidence passed to an answer model be
adjusted for each question instead of using the same BM25 depth every time?

I developed and ran the project locally between June and August 2026. I
organised the GitHub repository after the main experiments had finished, so the
commit history mainly records that later archive and upload process rather than
every local revision. Dates in the experiment notes refer to the protocol,
run, or check being recorded; they are not reconstructed commit dates.

## What the system does

The experiments use QASPER, a dataset of questions about scientific papers.
Each paper is converted into searchable evidence units: its abstract,
overlapping body-text chunks, table descriptions, figure captions, and other
figure or table text. BM25 ranks these units within the paper.

`ControllerV3` starts from a small global BM25 result and may add evidence from
particular sections, tables, or figures. Its branch is chosen from lexical cues
in the question. For example, a question about results receives a different
budget from a short definition question. This selection stage is deterministic
and makes no language-model calls.

One boundary is important. The controller decides its budget before reading
the retrieved evidence; it does not estimate whether that evidence is already
sufficient. The `Stop` action simply ends the selected rule branch. It is not
evidence-conditioned dynamic stopping.

The earlier Validation50 runs were used while developing the rules. I then
fixed ControllerV3 and evaluated it on the complete official QASPER test split.

## Results in brief

The main retrieval run contains 416 papers and 1,451 questions. At the
pre-specified evidence-overlap threshold of 0.5, the principal results are:

| Method | Evidence Recall | Question Hit Rate | Mean estimated tokens |
| --- | ---: | ---: | ---: |
| BM25 top-5 | 0.6149 | 0.8003 | 1,171 |
| BM25 top-7 | 0.7059 | 0.8624 | 1,629 |
| BM25 top-8 | 0.7442 | 0.8876 | 1,864 |
| BM25 top-10 | 0.8084 | 0.9127 | 2,305 |
| ControllerV3 | 0.7099 | 0.8706 | 1,638 |
| ControllerV3 without section expansion | 0.6879 | 0.8558 | 1,534 |

ControllerV3 and BM25 top-7 use almost the same mean evidence budget. Their
Evidence Recall difference is +0.0040, with a 95% paper-level paired bootstrap
interval of [-0.0118, +0.0184]. The Question Hit Rate difference is +0.0081
[-0.0044, +0.0210]. On this test set, neither metric shows a clear aggregate
advantage for the controller. This should not be read as a formal equivalence
result because no equivalence margin was specified.

I also compared the controller with generic BM25 additions while matching each
question's unit count or token budget. The Evidence Recall differences were
+0.0027 [-0.0060, +0.0110] and +0.0035 [-0.0051, +0.0118], respectively.
These controls suggest that the section rules did not add a clear aggregate
benefit beyond the extra evidence budget.

For a downstream check, I selected 53 complete paper clusters containing 201
questions and used the same local Qwen2.5-3B model for every method.
ControllerV3 obtained an Answer F1 of 0.3280, compared with 0.3278 for BM25
top-7. Their paired difference was +0.0002 [-0.0313, +0.0312]. This is a
sampled generation result, not a full 1,451-question generation evaluation.

## Running the code

Create a virtual environment and install the recorded dependencies:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

The retrieval and statistical scripts run without Ollama. Answer generation
also needs Ollama with the `qwen2.5:3b` model. The full Windows and macOS command
sequence is in the [reproduction guide](docs/REPRODUCTION_GUIDE_ZH.md).

If the local, Git-ignored raw outputs are available, the main checks are:

```bash
.venv/bin/python src/audit_test_experiment.py
.venv/bin/python src/audit_supplementary.py
.venv/bin/python src/audit_test_generation.py
```

The main scripts are:

- `src/build_evidence_units.py` builds the QASPER evidence units;
- `src/run_retrieval_experiment.py` runs BM25 and ControllerV3 retrieval;
- `src/bootstrap_retrieval.py` calculates paper-level bootstrap intervals;
- `src/run_supplementary_retrieval.py` runs the budget-matched controls;
- `src/analyze_controller_behavior.py` summarises controller paths and budgets;
- `src/build_test_generation_sample.py` creates the paper-cluster sample;
- `src/run_deduplicated_ollama_generation.py` runs each unique prompt once;
- `src/evaluate_test_generation.py` evaluates the generated answers.

## Repository contents

```text
src/                    experiment and audit scripts
data/processed/         development data; rebuilt test data are ignored
outputs/test416/        main retrieval summaries, intervals, and checks
outputs/supplementary/  matched controls, behaviour analysis, and generation
outputs/figures/        figures and their source/hash records
docs/                   protocols, results, data notes, and reproduction steps
```

The main written records are:

- [test evaluation protocol](docs/TEST_EVALUATION_PROTOCOL.md) and
  [retrieval results](docs/TEST416_RESULTS.md);
- [supplementary protocol](docs/SUPPLEMENTARY_EXPERIMENT_PROTOCOL.md) and
  [budget-matched results](docs/SUPPLEMENTARY_RETRIEVAL_RESULTS.md);
- [generation smoke check](docs/GENERATION_SMOKE_GATE.md) and
  [generation results](docs/TEST_GENERATION_RESULTS.md);
- [documentation index](docs/README.md), [data dictionary](docs/DATA_DICTIONARY_ZH.md),
  and [figure notes](docs/FIGURE_GUIDE.md).

## Data kept outside Git

QASPER is loaded from `allenai/qasper` at revision
`13b496d2a5359329b110e3419628de3cf791843b`. The processed full test set, local
model files, complete prompts and generations, and large per-question JSONL
files are not committed. Their file sizes and SHA-256 hashes are recorded in
the manifests under `outputs/test416/` and `outputs/supplementary/`.

The repository does include result tables, paired intervals, question-level
diagnostics, integrity checks, and figure provenance. The dissertation itself
is maintained separately in Overleaf.

## Limitations

- Evidence coverage is based on a project-specific lexical-overlap measure; it
  is not a direct test of semantic sufficiency.
- Retrieval-stage token cost is estimated as `words * 1.3`. Actual Ollama
  prompt-token counts are available only for the generation experiment.
- The controller inherits the weaknesses of BM25, hand-written lexical rules,
  overlapping chunks, and caption-only treatment of figures and tables.
- The downstream experiment uses one quantised 3B model and a 201-question
  sample.
- Analyses carried out after the main test result are labelled supplementary.
  Any method changed in response to them would need a new independent test set.

## Author

Ruotong Peng
