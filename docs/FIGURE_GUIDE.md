# Result figure guide

`src/make_thesis_figures.py` exports each figure as a vector PDF and a 400 dpi
RGB PNG at 160 mm width. The PDF is intended for document typesetting; the PNG
is retained for visual review and fallback use.

## Figure 1: retrieval quality–cost trade-off

Files: `outputs/figures/fig_retrieval_quality_cost.{pdf,png}`

Figure content:

> Held-out retrieval quality and estimated evidence-reading cost on the full
> QASPER test split (416 papers; 1,451 questions). Points show the mean Evidence
> Recall at token overlap at least 0.5 against mean estimated input tokens
> (words multiplied by 1.3); error bars are 95% paper-cluster bootstrap
> intervals from 5,000 replicates. ControllerV3 lies close to BM25 top-7 and to
> the question-level count-matched generic control. Abstract-only and read-all
> provide low- and high-cost reference points.

Interpretation boundary: this figure supports close aggregate location of
ControllerV3 and BM25 top-7. It does not establish statistical equivalence or
ControllerV3 superiority.

## Figure 2: paired retrieval contrasts

Files: `outputs/figures/fig_paired_retrieval_effects.{pdf,png}`

Figure content:

> Paired ControllerV3 retrieval contrasts on the QASPER test split. The upper
> panel reports Evidence Recall and Question Hit Rate differences in percentage
> points; the lower panel reports estimated-token differences. Bars are 95%
> paper-cluster bootstrap intervals from 5,000 replicates. Intervals for the
> cost-matched BM25 top-7 and generic count-matched quality contrasts include
> zero. The full controller has higher retrieval coverage than the no-section
> ablation while adding approximately 104 estimated tokens per question; this
> ablation alone does not separate section targeting from the larger budget.

## Figure 3: question-level budget redistribution

Files: `outputs/figures/fig_controller_budget_distribution.{pdf,png}`

Figure content:

> Distribution of the per-question difference in estimated evidence tokens
> between ControllerV3 and BM25 top-7 over all 1,451 test questions. Although
> the median difference is zero and the mean is approximately eight tokens,
> ControllerV3 uses a lower, equal, or higher budget for 26.1%, 29.6%, and 44.3%
> of questions, respectively. The controller therefore redistributes the
> evidence budget across questions without materially reducing its mean cost.

## Figure 4: frozen test-sample answer generation

Files: `outputs/figures/fig_generation_results.{pdf,png}`. This figure is only
created after the frozen generation evaluation has produced its summary and
bootstrap tables.

Figure content:

> Frozen supplementary test-sample answer-generation results for 53 complete paper clusters
> (201 questions), using Qwen2.5-3B with a fixed prompt and decoding settings.
> Panels report method-level Answer F1, paired ControllerV3 Answer F1
> differences, and actual Ollama prompt-token counts. Bars are 95%
> paper-cluster bootstrap intervals from 5,000 replicates. Identical prompts
> were generated once and reused across methods.

The numerical confidence intervals are reported in
`docs/TEST_GENERATION_RESULTS.md`. An interval containing zero does not establish
either a difference or formal equivalence.

## Provenance and accessibility

`outputs/figures/figure_manifest.json` records source paths and SHA-256 hashes,
transformations, output hashes, and alt text. Color is never the only method
encoding: method points also differ by marker shape, reference lines differ by
line style, and all comparisons are directly labelled. All panels use linear
axes; zero baselines are shown for difference plots.
