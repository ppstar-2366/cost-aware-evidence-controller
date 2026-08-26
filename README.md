# Cost-Aware Evidence Controller for Scientific QA

This project studies evidence selection for scientific paper question answering on QASPER.  
The main research question is:

> Can a lightweight, interpretable controller retrieve enough evidence for answer generation while reducing evidence-reading cost compared with larger fixed top-k retrieval?

The final system compares BM25 baselines with a rule-based, question-aware ControllerV3. It then uses a local Ollama model to generate answers from the retrieved evidence.

## Project structure

```text
src/
  common.py                    # shared JSONL/CSV IO, tokenization, QASPER answer parsing
  retrieval.py                 # BM25 retrieval, retrieval evaluation, cost estimation
  build_evidence_units.py      # build structured evidence units from QASPER
  run_controller_v3.py         # final cost-aware evidence controller
  run_retrieval_experiment.py  # unified retrieval + cost comparison pipeline
  build_generation_prompts.py  # convert retrieval outputs into LLM prompts
  run_ollama_generation.py     # local Ollama answer generation
  evaluate_generated_answers.py# answer F1 / exact match evaluation
  check_processed_data.py      # quick processed-data inspection
  audit_experiments.py         # verify all artifacts and refresh the archive

data/processed/
  qasper_train_100.jsonl
  qasper_validation_50.jsonl
  qasper_test_416.jsonl

outputs/
  validation50_bm25_top*.jsonl
  validation50_controller_v3.jsonl
  validation50_controller_v3_no_section.jsonl
  validation50_method_comparison_threshold05.csv
  error_analysis_controller_v3_validation50.csv
  generation_prompts_validation50.jsonl
  ollama_generations_validation50.jsonl
  ollama_answer_scores_validation50.csv
  ollama_answer_summary_validation50.csv
  test416/                       # frozen held-out retrieval and bootstrap artifacts

docs/
  README.md                     # Chinese archive index and migration notes
  EXPERIMENT_ARCHIVE_ZH.md      # complete work log, methods, results, limitations
  REPRODUCTION_GUIDE_ZH.md      # command-level reproduction guide
  DATA_DICTIONARY_ZH.md         # schemas and field meanings
  THESIS_WRITING_MATERIAL_ZH.md # thesis-ready structure and discussion points
  RESEARCH_REFLECTIONS_AND_CONCLUSIONS_ZH.md
  THESIS_EVIDENCE_MAP_ZH.md     # map thesis claims to auditable evidence
  TEST_EVALUATION_PROTOCOL.md   # pre-specified held-out evaluation protocol
  TEST416_RESULTS.md            # held-out results and defensible interpretation
  EXPERIMENT_GAP_AUDIT_ZH.md    # prioritized supplementary experiment plan
  SUPPLEMENTARY_EXPERIMENT_PROTOCOL.md # frozen follow-up experiment design
  SUPPLEMENTARY_RETRIEVAL_RESULTS.md # budget-matched and behaviour results
  experiment_audit.json         # machine-readable recomputed audit
  experiment_results_overview.csv
  file_manifest_sha256.csv
```

## Reproducible workflow

Use the project virtual environment when possible:

```bash
# macOS / Linux
.venv/bin/python src/check_processed_data.py \
  --input data/processed/qasper_test_416.jsonl
```

```powershell
# Windows
.\.venv\Scripts\python.exe src\check_processed_data.py
```

In VS Code, the repository includes workspace settings that select
`.venv/bin/python` and tasks for building the test split, running retrieval,
bootstrapping, and auditing the held-out artifacts.

If the processed QASPER files need to be rebuilt:

```powershell
.\.venv\Scripts\python.exe src\build_evidence_units.py
```

Run the retrieval experiment:

```powershell
.\.venv\Scripts\python.exe src\run_retrieval_experiment.py
```

Build generation prompts:

```powershell
.\.venv\Scripts\python.exe src\build_generation_prompts.py
```

Run local answer generation with Ollama:

```powershell
.\.venv\Scripts\python.exe src\run_ollama_generation.py --model qwen2.5:3b
```

Evaluate generated answers:

```powershell
.\.venv\Scripts\python.exe src\evaluate_generated_answers.py
```

Verify every saved artifact and refresh the portable experiment archive:

```powershell
.\.venv\Scripts\python.exe src\audit_experiments.py
```

For thesis writing or migration to another computer, start with
[`docs/README.md`](docs/README.md). The archive records the exact parameters,
all final results, file schemas, environment, prompt-cap caveat, error analysis,
and reproducibility limitations.

## Current research status

Completed:

- QASPER papers are converted into structured evidence units: title, abstract, section chunks, tables, and figure captions.
- BM25 baselines support top-k retrieval for k = 1, 3, 5, 10, 20.
- ControllerV3 implements interpretable question-aware retrieval actions:
  - start from a small top-ranked evidence budget;
  - expand evidence for result, dataset, method, definition, table, and figure-related questions;
  - apply section-aware expansion for dataset and definition questions.
- Retrieval quality is evaluated using gold-evidence token-overlap recall and question hit rate.
- Retrieval cost is estimated using retrieved units, words, and approximate token count.
- Validation50 retrieval results and error analysis have been produced.
- Local Ollama generation pipeline has been added and tested with `qwen2.5:3b`.
- A ControllerV3 ablation without section-aware expansion has been added.
- The generation prompt has been revised to use extractive short-answer behaviour, which is more suitable for a small local 3B model.
- Full local answer generation has been completed for all 624 prompts using `qwen2.5:3b`.
- The frozen ControllerV3 has been evaluated once on the full official QASPER
  test split (416 papers and 1,451 questions).
- Test results include cost-matched BM25 top-7/top-8 baselines, the no-section
  ablation, 5,000-replicate paper-level paired bootstrap intervals, and a
  passing alignment/hash audit.

Still recommended before final thesis submission:

- Use the held-out table and paired intervals from
  `docs/TEST416_RESULTS.md` as the primary retrieval evidence.
- Keep Validation50 and local generation results clearly labelled as
  development/downstream analyses rather than independent test results.
- Do not revise ControllerV3 from test error analysis and then report the same
  test set as an untouched evaluation.

## Current key results

Frozen retrieval evaluation on the official QASPER test split at the primary
evidence-overlap threshold 0.5:

| Method | Evidence recall | Question hit rate | Avg. estimated tokens | Recall / 1k tokens |
| --- | ---: | ---: | ---: | ---: |
| BM25_top5 | 0.6149 | 0.8003 | 1171 | 0.5251 |
| BM25_top7 | 0.7059 | 0.8624 | 1629 | 0.4333 |
| BM25_top8 | 0.7442 | 0.8876 | 1864 | 0.3992 |
| BM25_top10 | 0.8084 | 0.9127 | 2305 | 0.3507 |
| ControllerV3 | 0.7099 | 0.8706 | 1638 | 0.4334 |
| ControllerV3_no_section | 0.6879 | 0.8558 | 1534 | 0.4484 |

At almost identical estimated cost, ControllerV3 minus BM25 top-7 has an
Evidence Recall difference of +0.0040 (95% paired CI −0.0118 to +0.0184) and a
Question Hit Rate difference of +0.0081 (−0.0044 to +0.0210). The defensible
primary conclusion is closely matched aggregate point estimates and cost with
no clear paired difference, not superiority or formal statistical equivalence.
The section-aware expansion improves recall by +0.0220 (+0.0129 to +0.0310)
and hit rate by +0.0148 (+0.0046 to +0.0255), while adding about 104 estimated
tokens per question.

The earlier Validation50 results below are development results, because its
questions and error analysis informed ControllerV3.

Retrieval evaluation on `qasper_validation_50` at evidence-overlap threshold 0.5:

| Method | Evidence recall | Question hit rate | Avg. estimated tokens | Recall / 1k tokens |
| --- | ---: | ---: | ---: | ---: |
| BM25_top5 | 0.5646 | 0.7748 | 1156 | 0.4884 |
| BM25_top10 | 0.7772 | 0.9007 | 2322 | 0.3347 |
| BM25_top20 | 0.9519 | 0.9801 | 4144 | 0.2297 |
| ControllerV3 | 0.7063 | 0.8675 | 1640 | 0.4307 |
| ControllerV3_no_section | 0.6759 | 0.8344 | 1543 | 0.4380 |

Interpretation:

- ControllerV3 retrieves substantially less evidence than BM25_top10 while reaching a recall level between BM25_top5 and BM25_top10.
- Compared with the no-section ablation, full ControllerV3 improves evidence recall from 0.6759 to 0.7063 and question hit rate from 0.8344 to 0.8675.
- BM25_top20 has the highest recall but uses much more context, which supports the thesis motivation that fixed large top-k retrieval is costly.

Full local Ollama answer generation using `qwen2.5:3b`, 156 questions per method:

| Method | Answer F1 | Exact match | Success |
| --- | ---: | ---: | ---: |
| BM25_top5 | 0.2591 | 0.1218 | 156/156 |
| BM25_top10 | 0.2629 | 0.1282 | 156/156 |
| BM25_top20 | 0.2577 | 0.1218 | 156/156 |
| ControllerV3 | 0.2577 | 0.1218 | 156/156 |

The answer-generation results show that the lower-cost ControllerV3 evidence set can support downstream local answer generation at a level comparable to fixed top-k baselines. Because the generator is a lightweight local 3B model, the thesis should emphasize retrieval quality, cost, ablation, and error analysis, while using answer F1 / EM as downstream validation.

Note: the wall-clock time fields in the generation CSV are diagnostic only. The full generation run was completed through interrupted/resumed sessions, so thesis tables should cite Answer F1, EM, success rate, and token statistics rather than wall-clock time.

## Thesis writing angle

A strong thesis structure can be:

1. Problem: scientific QA requires evidence grounding, but fixed large top-k retrieval increases cost.
2. Baseline: BM25 top-k retrieval provides a transparent lexical retrieval baseline.
3. Proposed method: a lightweight controller uses interpretable question-type
   and section-aware rules to allocate a variable evidence budget.
4. Evaluation:
   - evidence recall and hit rate measure retrieval quality;
   - average retrieved tokens measure cost;
   - recall per 1k tokens measures cost-effectiveness;
   - answer F1 / EM measures downstream QA utility.
5. Analysis: error categories show when the controller fails and what future improvements are needed.

The budget-matched section controls and controller-behaviour analysis are now
complete. They do not establish an aggregate retrieval-quality advantage for
section-aware targeting over generic additions at the same question-specific
budget. The next experiment is the frozen, prompt-audited held-out generation
sample specified in
[`docs/SUPPLEMENTARY_EXPERIMENT_PROTOCOL.md`](docs/SUPPLEMENTARY_EXPERIMENT_PROTOCOL.md).
