# QASPER Test Evaluation Protocol

Recorded on 27 August 2026 (Asia/Shanghai), before the test output was
inspected.

I used the settings below for the held-out evaluation. I did not use the test
questions, gold evidence, or results to revise ControllerV3 or to choose the
reported thresholds, baselines, or metrics.

## Method state

- Remote baseline commit: `c7ec037c413e0ac30b9b2050aa8f7ec73a643465`
- Controller: `ControllerV3`, a rule-based, question-aware variable-budget
  evidence controller.
- Controller source SHA-256:
  `96d5d3391b4372816507138e9013870df4b22e2328019e1111b009be91949166`
- Remote-baseline retrieval source SHA-256 (before run-naming infrastructure):
  `fca38a2ed09d71c103049366ae9d6c0b812f2e781dcea8e99cb520ebe5b113a0`
- Shared metric source SHA-256:
  `2338ff4c992f9554c4c5d6d91add29306e887b85fbe9306bac34628f96ea247e`

The ControllerV3 code is the same as in the remote baseline. The later changes
only added test-split processing, run-specific filenames, cost-matched fixed-k
baselines, and bootstrap analysis.

## Data

- Dataset: `allenai/qasper`
- Pinned revision: `13b496d2a5359329b110e3419628de3cf791843b`
- Split: complete official `test` split
- Expected size: 416 papers and 1,451 questions
- Processed output: `data/processed/qasper_test_416.jsonl`

No test-specific preprocessing, keyword, threshold, or controller rule will be
introduced after results are observed.

## Methods

The following methods will be run on identical processed papers and questions:

- BM25 top-1
- BM25 top-3
- BM25 top-5
- BM25 top-7
- BM25 top-8
- BM25 top-10
- BM25 top-20
- ControllerV3
- ControllerV3 without section-aware expansion

Top-7 and top-8 are included as pre-specified cost-matched fixed-budget
comparators. On the development subset, BM25 top-7 uses 1,636 estimated tokens
per question versus 1,640 for ControllerV3, whereas top-8 uses 1,850. ControllerV3
versus BM25 top-7 is therefore the primary adaptive-versus-fixed comparison.
ControllerV3 versus BM25 top-8, BM25 top-10, and the no-section ablation are
additional planned comparisons.

## Metrics

Primary threshold: token-set gold-evidence overlap >= 0.5.

Primary reported metrics:

- Evidence Recall
- Question Hit Rate
- Average Best Overlap
- Average Retrieved Units
- Average Estimated Evidence Tokens (`words * 1.3`)
- Recall per 1,000 Estimated Tokens

Thresholds 0.3 and 0.7 are pre-specified sensitivity analyses. The overlap
metrics and estimated-token cost are project-specific proxies rather than the
official QASPER Evidence-F1 or a model-tokenizer cost.

## Uncertainty analysis

- 5,000 bootstrap replicates
- Random seed: 42
- Resampling unit: paper
- All questions belonging to a sampled paper remain together
- Identical resampled paper indices are used for every method
- 95% percentile confidence intervals
- Paired confidence intervals are computed directly for method differences

Planned paired contrasts:

- ControllerV3 - BM25 top-5
- ControllerV3 - BM25 top-7
- ControllerV3 - BM25 top-8
- ControllerV3 - BM25 top-10
- ControllerV3 - ControllerV3 without section-aware expansion

Separate method confidence-interval overlap will not be used as a significance
test. Interpretation will lead with point differences and their paired
confidence intervals.

## Artifact isolation

All held-out outputs will be stored under `outputs/test416/` and prefixed with
`test416_`. Existing `validation50_*` data will not be overwritten. Test error
analysis may be performed after the frozen evaluation, but its findings will
not be used to revise the method reported against this test set.

## Work outside this evaluation

Full test-split Ollama generation, a dense retriever, and a new dynamic-stopping
ControllerV4 are outside this primary evaluation. Any later analysis using the
same test split is marked as supplementary.

## Run record

The run finished on 27 August 2026 without changes to ControllerV3. The
processed split contained the expected 416 papers and 1,451 questions. It
produced nine method outputs, 5,000-replicate paper-level bootstrap intervals,
error-analysis files, and a SHA-256 manifest under `outputs/test416/`.

The automated alignment audit passed. The processed test file SHA-256 is
`ec8e3166a18da3b4347e8f12252b9eecdaa271d2694986145d35e84a0ce8e792`.
The executed retrieval runner SHA-256, after infrastructure-only output naming
changes, is
`6865a27ce7c2f2d2a5e3ece778242b02f78c1204c22c0d6c18623918d080c131`.
Results and their interpretation are recorded in `docs/TEST416_RESULTS.md`.
