# Supplementary Retrieval and Controller-Behaviour Results

Run date: 2026-08-27. These analyses use the complete official QASPER test
split (416 papers, 1,451 questions) after the primary test result was known.
They are therefore supplementary and do not replace the frozen primary
ControllerV3 versus BM25 top-7 comparison.

## Integrity and statistical design

- ControllerV3 and its primary test outputs remained frozen.
- Every supplementary method produced 1,451 uniquely aligned question rows.
- GenericCountMatched exactly matched the ControllerV3 unit count for every
  question.
- GenericTokenMatched exactly matched retrieved words for 1,051/1,451
  questions; its mean absolute residual was 14.31 words and its maximum was
  125 words.
- All intervals below are 95% percentile intervals from 5,000 paired
  paper-cluster bootstrap samples with seed 42.
- `src/audit_supplementary.py` passed all completeness, alignment, budget, and
  bootstrap-configuration checks.

## Retrieval reference points

| Method | Evidence Recall | Question Hit Rate | Avg. units | Est. tokens | Recall / 1k tokens |
|---|---:|---:|---:|---:|---:|
| AbstractOnly | 0.1063 | 0.2078 | 1.00 | 178 | 0.5978 |
| ControllerV3 | 0.7099 | 0.8706 | 7.76 | 1,638 | 0.4335 |
| GenericCountMatched | 0.7072 | 0.8639 | 7.76 | 1,645 | 0.4299 |
| GenericTokenMatched | 0.7064 | 0.8654 | 7.75 | 1,637 | 0.4316 |
| ReadAll | 0.9973 | 1.0000 | 29.43 | 5,130 | 0.1944 |

Abstract-only is cheap but misses most annotated evidence. Read-all establishes
that nearly all gold evidence is recoverable from the constructed evidence
units, but at more than three times ControllerV3's estimated token cost. These
two rows are reference points rather than competitive baselines.

## Budget-matched mechanism contrasts

| Contrast: ControllerV3 minus control | Point difference | 95% interval |
|---|---:|---:|
| Count-matched Evidence Recall | +0.0027 | [-0.0060, +0.0110] |
| Count-matched Question Hit Rate | +0.0067 | [-0.0015, +0.0153] |
| Count-matched Average Best Overlap | +0.0030 | [-0.0027, +0.0086] |
| Count-matched estimated tokens | -7.57 | [-13.23, -1.64] |
| Count-matched Recall / 1k tokens | +0.0036 | [-0.0019, +0.0089] |
| Token-matched Evidence Recall | +0.0035 | [-0.0051, +0.0118] |
| Token-matched Question Hit Rate | +0.0052 | [-0.0037, +0.0141] |
| Token-matched Average Best Overlap | +0.0036 | [-0.0018, +0.0091] |
| Token-matched estimated tokens | +1.05 | [-1.23, +3.27] |
| Token-matched Recall / 1k tokens | +0.0019 | [-0.0034, +0.0069] |

The intervals for retrieval-quality and efficiency differences all include
zero. The data therefore do not establish that ControllerV3's section-aware
selection improves aggregate retrieval over generic BM25 additions at the same
question-specific budget. The small point differences should not be described
as a demonstrated gain. Against the exact count-matched control, ControllerV3
does use approximately 7.6 fewer estimated tokens on average, reflecting
slightly shorter selected units; this cost difference is small relative to the
overall budget.

This result sharpens the full-versus-no-section ablation. Section-aware
expansion improved recall over the lower-cost no-section variant, but the
budget-matched controls show that the improvement cannot be attributed
confidently to section targeting rather than adding evidence budget.

## Variable-budget behaviour

ControllerV3 retrieved 7.76 units on average (SD 2.24; median 7; P10 5; P90
11) and used an estimated 1,637.55 tokens on average (SD 461.73; median
1,618.50). Relative to BM25 top-7, its paired token difference had mean +8.11,
median 0, P10 -525.20, and P90 +514.80 tokens. It used a lower budget for 379
questions (26.1%), the same budget for 429 (29.6%), and a higher budget for 643
(44.3%). Thus, the controller's defining behaviour is redistribution of a
similar aggregate budget across questions, not a lower overall mean budget.

The mutually exclusive implementation paths were:

| Path | Questions | Evidence Recall | Hit Rate | Avg. units | Est. tokens |
|---|---:|---:|---:|---:|---:|
| Definition | 139 | 0.5908 | 0.7895 | 4.87 | 1,147 |
| Result/data | 643 | 0.7918 | 0.9217 | 9.90 | 1,897 |
| Method/complex | 427 | 0.6992 | 0.8487 | 7.04 | 1,665 |
| Default | 242 | 0.5961 | 0.8210 | 5.02 | 1,180 |

These path results are descriptive. Path membership is determined by question
wording, so differences between paths must not be interpreted as causal effects
of allocating more evidence. In particular, the result/data path both receives
the largest budget and may contain questions with different intrinsic
retrieval difficulty.

## Interpretation boundary

ControllerV3 is best described as a lightweight, interpretable,
question-type-aware variable-budget controller. On the held-out test split, it
redistributes evidence cost substantially at the question level while keeping
mean cost close to a fixed top-7 baseline. Its aggregate retrieval performance
is also close to budget-matched generic selection, and the present experiment
does not demonstrate an independent benefit from section-aware targeting. This
result limits the supported claim to transparent budget redistribution and
motivates evidence-sufficiency estimation or stronger reranking as future work.

## Reproduction

```bash
.venv/bin/python src/run_supplementary_retrieval.py
.venv/bin/python src/bootstrap_supplementary.py
.venv/bin/python src/analyze_controller_behavior.py
.venv/bin/python src/audit_supplementary.py
```

Machine-readable results and the SHA-256 manifest are under
`outputs/supplementary/`. Large per-question JSONL files remain local and are
ignored by Git.
