# QASPER Test Retrieval Results

Run completed: 27 August 2026 (Asia/Shanghai)

## Data checked

The evaluation covers the full official QASPER test split: 416 papers and
1,451 questions. Of these, 1,352 questions contain gold
evidence and contribute to Evidence Recall and Question Hit Rate. Every method
produced one aligned record for each of the 1,451 questions. The automated audit
passed with no duplicate, missing, or unexpected paper-question keys.

ControllerV3 was not changed after the test results were observed. It should be
described as a rule-based, question-aware variable-budget evidence controller,
not as evidence-sufficiency-based dynamic stopping.

## Main results at the pre-specified 0.5 threshold

| Method | Evidence Recall (95% CI) | Question Hit Rate (95% CI) | Estimated tokens (95% CI) |
|---|---:|---:|---:|
| BM25 top-1 | 0.2187 (0.1996–0.2390) | 0.3824 (0.3559–0.4098) | 223.7 (217.9–229.7) |
| BM25 top-3 | 0.4592 (0.4343–0.4843) | 0.6657 (0.6391–0.6925) | 693.9 (681.4–706.2) |
| BM25 top-5 | 0.6149 (0.5876–0.6417) | 0.8003 (0.7780–0.8225) | 1,170.6 (1,151.4–1,190.3) |
| BM25 top-7 | 0.7059 (0.6817–0.7303) | 0.8624 (0.8429–0.8810) | 1,629.4 (1,603.0–1,655.6) |
| BM25 top-8 | 0.7442 (0.7216–0.7673) | 0.8876 (0.8697–0.9041) | 1,863.5 (1,833.4–1,893.8) |
| BM25 top-10 | 0.8084 (0.7878–0.8283) | 0.9127 (0.8975–0.9274) | 2,304.7 (2,264.9–2,343.5) |
| BM25 top-20 | 0.9538 (0.9435–0.9633) | 0.9867 (0.9800–0.9931) | 4,014.3 (3,909.3–4,119.5) |
| ControllerV3 | 0.7099 (0.6838–0.7361) | 0.8706 (0.8517–0.8883) | 1,637.5 (1,604.0–1,669.9) |
| ControllerV3 without section expansion | 0.6879 (0.6615–0.7136) | 0.8558 (0.8356–0.8746) | 1,533.6 (1,505.4–1,561.4) |

Confidence intervals are 95% percentile intervals from 5,000 bootstrap samples
of papers, using seed 42. Questions from the same paper remain clustered.

## Pre-specified paired comparisons

The primary comparison is ControllerV3 minus BM25 top-7 because their estimated
evidence costs are almost identical.

| Comparison | Metric | Difference (95% paired CI) | Interpretation |
|---|---|---:|---|
| ControllerV3 − BM25 top-7 | Evidence Recall | +0.0040 (−0.0118 to +0.0184) | No clear aggregate difference |
| ControllerV3 − BM25 top-7 | Question Hit Rate | +0.0081 (−0.0044 to +0.0210) | No clear aggregate difference |
| ControllerV3 − BM25 top-7 | Estimated tokens | +8.1 (−13.4 to +29.4) | Costs are closely matched |
| ControllerV3 − BM25 top-5 | Evidence Recall | +0.0950 (+0.0809 to +0.1087) | Higher coverage at higher cost |
| ControllerV3 − BM25 top-5 | Estimated tokens | +467.0 (+444.1 to +489.3) | Substantially higher cost |
| ControllerV3 − BM25 top-8 | Evidence Recall | −0.0344 (−0.0506 to −0.0189) | Lower coverage at lower cost |
| ControllerV3 − BM25 top-8 | Estimated tokens | −226.0 (−248.4 to −203.6) | Substantially lower cost |
| ControllerV3 − no-section ablation | Evidence Recall | +0.0220 (+0.0129 to +0.0310) | Higher coverage with a larger budget |
| ControllerV3 − no-section ablation | Question Hit Rate | +0.0148 (+0.0046 to +0.0255) | Higher hit rate with a larger budget |
| ControllerV3 − no-section ablation | Estimated tokens | +104.0 (+91.1 to +117.1) | The full method reads more evidence |

The aggregate point estimates and costs are close to those of the top-7
baseline, and the paired intervals do not show a clear difference. This is not
a formal equivalence result because I did not specify an equivalence margin or
test in advance.
ControllerV3 lies between top-7 and top-8 on the empirical cost–coverage trade-off.
The full method has higher coverage than the no-section ablation, but it also
reads more evidence and lowers Recall per 1,000 estimated tokens at threshold
0.5 by 0.0150 (95% paired CI −0.0207 to −0.0096). This contrast alone does not
isolate section targeting from the additional budget; the matched controls in
`SUPPLEMENTARY_RETRIEVAL_RESULTS.md` address that distinction.

## Threshold sensitivity

The primary threshold remains 0.5. At the pre-specified 0.3 threshold,
ControllerV3 and top-7 are again indistinguishable in the paired intervals. At
the stricter 0.7 threshold, ControllerV3 has higher Evidence Recall by 0.0207
(95% paired CI +0.0046 to +0.0360) and higher Question Hit Rate by 0.0222
(+0.0059 to +0.0385). This is a sensitivity result, not a replacement for the
primary analysis, and should be labelled accordingly.

## Reproducibility artifacts

- Processed test SHA-256:
  `ec8e3166a18da3b4347e8f12252b9eecdaa271d2694986145d35e84a0ce8e792`
- Frozen ControllerV3 SHA-256:
  `96d5d3391b4372816507138e9013870df4b22e2328019e1111b009be91949166`
- Retrieval runner SHA-256:
  `6865a27ce7c2f2d2a5e3ece778242b02f78c1204c22c0d6c18623918d080c131`
- Bootstrap script SHA-256:
  `31af781dcb48e9caed4ed8bc02e01fcd3e921988c1b73c162994318b9d9e8d44`
- Full hashes and sizes: `outputs/test416/test416_sha256_manifest.csv`
- Machine-readable audit: `outputs/test416/test416_audit.json`

These results concern retrieval only. Estimated tokens are evidence words
multiplied by 1.3, rather than tokenizer counts or measured Ollama usage. The
separate generation experiment checks whether the retrieval differences carry
through to answers.
