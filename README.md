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

docs/
  README.md                     # Chinese archive index and migration notes
  EXPERIMENT_ARCHIVE_ZH.md      # complete work log, methods, results, limitations
  REPRODUCTION_GUIDE_ZH.md      # command-level reproduction guide
  DATA_DICTIONARY_ZH.md         # schemas and field meanings
  THESIS_WRITING_MATERIAL_ZH.md # thesis-ready structure and discussion points
  RESEARCH_REFLECTIONS_AND_CONCLUSIONS_ZH.md
  THESIS_EVIDENCE_MAP_ZH.md     # map thesis claims to auditable evidence
  experiment_audit.json         # machine-readable recomputed audit
  experiment_results_overview.csv
  file_manifest_sha256.csv
```

## Reproducible workflow

Use the project virtual environment when possible:

```powershell
.\.venv\Scripts\python.exe src\check_processed_data.py
```

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

Still recommended before final thesis submission:

- Discuss failure categories from `error_analysis_controller_v3_validation50.csv`.
- Use the final retrieval, ablation, and answer-generation tables in the thesis.

## Current key results

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
3. Proposed method: a cost-aware controller dynamically selects evidence actions by question type.
4. Evaluation:
   - evidence recall and hit rate measure retrieval quality;
   - average retrieved tokens measure cost;
   - recall per 1k tokens measures cost-effectiveness;
   - answer F1 / EM measures downstream QA utility.
5. Analysis: error categories show when the controller fails and what future improvements are needed.
