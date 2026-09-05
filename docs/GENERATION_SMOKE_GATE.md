# Generation Smoke Check

Check completed: 27 August 2026. This was a small execution check before the
201-question generation run. Its answer scores are not reported as experimental
results and were not used to change the sample, prompts, retrieval methods, or
ControllerV3.

## Frozen sample and prompts

- 53 whole-paper clusters selected with `random.Random(42)` after sorting paper
  IDs;
- 201 questions, exceeding the pre-specified minimum of 200 only because the
  final paper was retained in full;
- four aligned methods and 804 method-question records;
- 608 unique complete prompts after SHA-256 deduplication (24.4% reuse);
- no retrieved evidence was truncated by the 20,000-character safety bound;
- maximum retained evidence was 16,339 characters.

The paper and question IDs were written to
`outputs/supplementary/generation/test_generation_sample_manifest.json` before
prompt construction.

## Completion-budget amendment

The first 20-question run used the initially specified `num_predict=128`. All
67 unique prompts completed at the API level, but two returned
`done_reason=length`; one answer was visibly incomplete. This failed the planned
completion check; it was not used as a comparison of answer quality.

The only amended parameter was `num_predict=256`. The same 20 questions,
evidence, prompt hashes, model, seed, and four methods were rerun from a new
output file. The original 128-token runner audit is retained as provenance.

## Repeat with a 256-token output limit

| Check | Result |
|---|---:|
| Questions | 20 |
| Method-question records | 80 |
| Unique model calls | 67 |
| Successful unique calls | 67/67 |
| Length stops | 0 |
| Maximum output tokens | 142/256 |
| Maximum prompt tokens | 3,247/8,192 |
| Identical-prompt answer reuse | passed |
| Method/question alignment | passed |

The repeated sample passed the schema, deduplication, parsing, token,
completion, and alignment checks. I then ran the 201-question sample with
`temperature=0`, `seed=42`, `num_ctx=8192`, and
`num_predict=256`. The runner and independent integrity audit both now treat a
`done_reason=length` record as a failed completion rather than a successful
API call.

## Reproduction

```bash
.venv/bin/python src/build_test_generation_sample.py
.venv/bin/python src/run_deduplicated_ollama_generation.py \
  --output outputs/supplementary/generation/test_generation_smoke256_unique_generations.jsonl \
  --limit-questions 20
.venv/bin/python src/evaluate_test_generation.py \
  --generations outputs/supplementary/generation/test_generation_smoke256_unique_generations.jsonl \
  --prefix test_generation_smoke256 --limit-questions 20
.venv/bin/python src/audit_test_generation.py \
  --generations outputs/supplementary/generation/test_generation_smoke256_unique_generations.jsonl \
  --prefix test_generation_smoke256 --limit-questions 20
```
