# QASPER Test-Sample Answer Generation

Run completed: 27 August 2026. The independent integrity check passed.

## Scope

This is the pre-specified supplementary downstream evaluation described in
`SUPPLEMENTARY_EXPERIMENT_PROTOCOL.md`. Fifty-three complete paper clusters
were selected from the official QASPER test split after sorting paper IDs and
shuffling with `random.Random(42)`, retaining every question from the last
paper. The frozen sample contains 201 questions.

The comparison covers ControllerV3, BM25 top-7, BM25 top-8, and ControllerV3
without section expansion. All methods use the same prompt template and local
`qwen2.5:3b` model with `temperature=0`, `seed=42`, `num_ctx=8192`, and
`num_predict=256`. No selected evidence was truncated by the 20,000-character
safety bound. Identical complete prompts were generated once and their answers
were reused across methods.

Because the official test split had already been used for the primary frozen
retrieval evaluation before this supplementary protocol was written, this
sample is not presented as a newly untouched split. ControllerV3, the sample,
the prompt, and decoding settings were nevertheless frozen before inspecting
these generated answers.

## Main results

All 804 method-question records are present and all 608 unique model calls
completed successfully.

| Method | Answer F1 | 95% paper-bootstrap CI | EM | Actual prompt tokens | Actual output tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| BM25 top-7 | 0.3278 | [0.2710, 0.3875] | 0.2040 | 1,992.46 | 11.55 |
| BM25 top-8 | 0.3468 | [0.2915, 0.4053] | 0.2040 | 2,269.81 | 12.81 |
| ControllerV3 | 0.3280 | [0.2756, 0.3850] | 0.2090 | 2,050.92 | 12.05 |
| No section expansion | 0.3137 | [0.2632, 0.3664] | 0.1891 | 1,922.34 | 12.98 |

Intervals use 5,000 percentile bootstrap replicates with paper as the
resampling unit and seed 42. Prompt-token counts are Ollama
`prompt_eval_count`, not the retrieval-stage `words × 1.3` estimate.

## Pre-specified paired contrasts

Differences are first method minus second method.

| Contrast | Answer F1 difference | 95% paired CI | EM difference | Prompt-token difference | 95% paired CI |
| --- | ---: | ---: | ---: | ---: | ---: |
| ControllerV3 − BM25 top-7 | +0.0002 | [−0.0313, +0.0312] | +0.0050 | +58.46 | [−1.75, +115.19] |
| ControllerV3 − BM25 top-8 | −0.0188 | [−0.0502, +0.0134] | +0.0050 | −218.89 | [−284.74, −154.61] |
| ControllerV3 − no section | +0.0143 | [−0.0083, +0.0385] | +0.0199 | +128.58 | [+94.02, +165.62] |

The primary ControllerV3-versus-top-7 Answer F1 difference is effectively
zero at the point estimate, with an interval spanning approximately ±3.1 F1
percentage points. This supports a finding of no clear sampled difference; it
does not prove statistical equivalence.

BM25 top-8 has the highest numerical F1 and uses about 219 more prompt tokens
than ControllerV3. Its paired F1 interval still includes zero. Section
expansion increases actual input cost by about 129 prompt tokens relative to
the no-section ablation, while its sampled F1 increase remains uncertain. The
paired EM intervals also include zero for all three comparisons.

## Answer-type diagnostics

| Method | Extractive F1 (n) | Abstractive F1 (n) | Boolean F1 (n) | None F1 (n) | Unanimous-unanswerable accuracy (10 q) |
| --- | ---: | ---: | ---: | ---: | ---: |
| BM25 top-7 | 0.3132 (90) | 0.1303 (59) | 0.4000 (30) | 0.8182 (22) | 0.90 |
| BM25 top-8 | 0.3655 (91) | 0.1455 (58) | 0.3667 (30) | 0.7727 (22) | 0.80 |
| ControllerV3 | 0.3149 (92) | 0.1200 (58) | 0.3929 (28) | 0.8261 (23) | 0.90 |
| No section expansion | 0.2947 (91) | 0.1248 (58) | 0.3448 (29) | 0.8261 (23) | 0.90 |

QASPER questions can contain reference answers of multiple types. The table
groups each method-question record by the type of its best-F1 reference, so the
group sizes can differ by method. These values are descriptive diagnostics,
not aligned subgroup tests. Unanswerable accuracy is separately restricted to
the ten questions whose references are unanimously unanswerable.

## Prompt deduplication and integrity

- 53 papers, 201 questions, four methods, 804 aligned method-question rows;
- 608 unique complete prompts and 196 reused method-question rows, a 24.38%
  reuse rate;
- 608/608 successful complete calls, with no missing, unexpected, failed, or
  `done_reason=length` records;
- maximum retained evidence: 16,339 characters;
- maximum prompt: 3,796/8,192 tokens; maximum output: 236/256 tokens;
- actual unique-call cost: 1,273,451 prompt tokens and 7,294 output tokens;
- without prompt deduplication the same 804 records would account for
  1,655,341 prompt tokens and 9,927 output tokens;
- deduplication therefore avoided 381,890 prompt tokens and 2,633 output
  tokens, while also preventing runtime nondeterminism from creating
  differences for identical inputs.

The local model inventory records Qwen2.5 3.1B, Q4_K_M quantization, digest
`357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`.

## Interpretation

With this local 3B model and the 201-question paper-cluster sample,
ControllerV3 and BM25 top-7 produced almost identical aggregate Answer F1 point
estimates. The paired interval did not show a clear difference. BM25 top-8
read more evidence and had the highest numerical F1, although its sampled F1
advantage over ControllerV3 remained uncertain. Section expansion also raised
prompt cost relative to the no-section version without a clear sampled F1 gain.

These findings are specific to one small local model and one supplementary
sample. They neither establish formal equivalence or superiority nor represent
a full 1,451-question generation evaluation. They also do not change the fact
that the current `Stop` action is rule-based rather than evidence-conditioned.

## Saved result files

- method summary: `test_generation_answer_summary.csv`;
- type diagnostics: `test_generation_answer_by_type.csv`;
- method and paired bootstrap: `test_generation_answer_bootstrap_*.csv`;
- answer-score and integrity audits: `test_generation_answer_audit.json` and
  `test_generation_integrity_audit.json`;
- source/output hashes: `test_generation_sha256_manifest.csv`;
- result figure: `outputs/figures/fig_generation_results.{pdf,png}`.

All generation result files are under `outputs/supplementary/generation/`.
Large raw prompt and generation JSONL files remain local and Git-ignored; their
hashes and byte sizes are retained in the committed manifest.
