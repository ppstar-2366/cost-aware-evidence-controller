# Dissertation Plan

## Working title

**Question-Aware Variable-Budget Evidence Selection for Scientific Paper Question Answering**

The title deliberately avoids claiming evidence-sufficiency-based stopping: the frozen ControllerV3 stops after completing explicit rule branches rather than iteratively estimating whether the collected evidence is sufficient.

## Thesis contract

- **Audience:** Imperial College London Department of Computing MSc project markers, including a second marker who may not have followed the project during development.
- **Document type:** MSc Computing (Artificial Intelligence and Machine Learning) final individual project report.
- **Language and style:** UK English; concise academic prose; Vancouver numeric citations.
- **Length:** target 40--50 A4 content pages; hard maximum 60 content pages. Title matter, contents, references, declarations, and appendices are excluded from the content-page count.
- **Format:** minimum 11 pt, approximately 2.5 cm margins, self-contained report, no source-code listings in the dissertation.
- **Primary empirical evidence:** frozen ControllerV3 evaluated on the complete official QASPER test split (416 papers; 1,451 questions), with paper-level paired bootstrap intervals.
- **Secondary empirical evidence:** frozen 201-question generation sample using Qwen2.5-3B; clearly labelled supplementary rather than a new untouched test evaluation.
- **Development evidence:** QASPER validation_50 is reported only as development history and diagnostic evidence, never as held-out final evaluation.

## Central research question

Can an inexpensive, interpretable, question-aware controller allocate a variable evidence budget for scientific paper question answering while retaining retrieval and downstream answer quality close to cost-matched fixed-depth BM25 retrieval?

## Supporting research questions

1. How does evidence coverage change as a fixed BM25 evidence budget increases?
2. Does ControllerV3 occupy a useful quality--cost operating point relative to fixed top-*k* baselines?
3. What does section-aware expansion add, and can its effect be separated from the effect of simply reading more units?
4. Does the controller preserve answer quality under a fixed local generation setting?
5. Which design assumptions and failure modes limit the conclusions?

## Main contribution claims

1. A reproducible pipeline converts QASPER papers into typed evidence units spanning abstracts, body chunks, table captions, and figure captions.
2. ControllerV3 provides a lightweight, explicit, question-aware policy that allocates different evidence budgets and records its actions without model calls during evidence selection.
3. A held-out evaluation reports evidence quality and cost jointly and uses paired paper-level bootstrap intervals instead of relying only on point estimates.
4. Budget-matched mechanism analysis shows that the apparent benefit of section expansion is largely explained by added evidence budget; this negative result sharpens the interpretation of the method.
5. A frozen local-generation study and experiment audits expose the distinction between retrieved evidence cost, prompt cost, and actual model tokens.

## Claim boundaries

- Do not call ControllerV3 an evidence-sufficiency estimator or iterative dynamic-stopping policy.
- Do not claim statistical significance or equivalence where a 95% interval crosses zero.
- Do not claim that section targeting independently improves aggregate retrieval at matched budget.
- Do not claim state-of-the-art performance or generalisation beyond QASPER.
- Do not use wall-clock time to compare methods.
- Treat estimated tokens (word count multiplied by 1.3) as a proxy, not tokenizer output.

## Chapter architecture

1. **Introduction:** problem, motivation, research questions, contributions, scope, report map.
2. **Background and Related Work:** scientific document QA; lexical and neural retrieval; RAG; adaptive retrieval; long-context limitations; cost-aware routing; precise gap and positioning.
3. **System Design and Implementation:** evidence units; BM25 candidate ranking; rule-based question classification; ControllerV3 actions; stopping semantics; prompt construction; implementation and reproducibility.
4. **Experimental Methodology:** datasets and split discipline; baselines; metrics; bootstrap procedure; primary and supplementary protocols; threats anticipated by design.
5. **Results:** fixed-budget frontier; controller vs cost-matched baselines; ablation and mechanism controls; controller behaviour; generation sample; diagnostic cases.
6. **Discussion:** interpretation, why larger context is not free, what the matched-budget negative result means, development-to-final scope change, limitations and validity threats.
7. **Conclusion and Future Work:** direct answers to research questions, contributions, limitations, evidence-sufficiency ControllerV4 and stronger retrieval as future work.
8. **References, Declarations, Appendices:** Vancouver references with DOI links; required declarations; protocols, supplementary tables, and reproducibility details.

## Figure story

1. System overview and evidence-flow diagram.
2. Retrieval quality versus estimated evidence cost.
3. Paired retrieval effects with 95% confidence intervals.
4. Controller evidence-budget distribution.
5. Supplementary generation results and actual prompt-token costs.

## Tables

1. QASPER split and evidence-unit statistics.
2. Controller action definitions and triggers.
3. Primary test retrieval results.
4. Primary paired comparisons.
5. Matched-budget mechanism analysis.
6. Frozen generation-sample results.
7. Main limitations and corresponding mitigations.

## Completion gates

- Every quantitative claim traces to a versioned CSV/JSON audit file.
- Every literature claim traces to a primary source and verified BibTeX record.
- All citations use non-breaking spaces before `\\cite{}`.
- The PDF compiles without errors, missing references, or overflowing tables.
- The abstract is written after the body and includes concrete final results without citations.
- Declarations accurately disclose the use of generative AI; the author must review and approve their wording.

