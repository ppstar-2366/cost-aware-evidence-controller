# Literature Review Contract

## Purpose

Position a lightweight, rule-based evidence-budget controller for single-paper scientific QA against four adjacent research lines: scientific document QA, retrieval-augmented generation, adaptive retrieval, and cost-aware inference. The review must explain why the project studies the decision layer between retrieval and generation rather than proposing a new retriever or language model.

## Scope

- **Core task:** information-seeking QA over full scientific papers with annotated supporting evidence.
- **Core mechanism:** question-conditioned selection of typed evidence units within one bounded document.
- **Comparators:** fixed-depth lexical retrieval, dense/late-interaction retrieval, read-all long-context use, model-based adaptive retrieval, and routing/cost-aware computation.
- **Time range:** seminal foundations plus primary work available through August 2026 when it materially affects positioning.
- **Sources:** peer-reviewed papers and official dataset/system documentation. Preprints may be used only where no archival version is available and must be labelled accurately.
- **Exclusions:** generic agent surveys without a direct connection to retrieval decisions; marketing pages; unverified secondary summaries; results that cannot be tied to an exact table, page, or official abstract.

## Review questions

1. What makes scientific document QA an evidence-localisation problem as well as an answer-generation problem?
2. Which fixed and learned retrieval methods define reasonable evidence-selection baselines?
3. How do adaptive retrieval systems decide whether, when, or how often to retrieve?
4. What evidence supports the claim that longer context is not a free substitute for selection?
5. How have cost, routing, and adaptive computation been operationalised in language-model systems?
6. Which gap remains for interpretable, typed evidence selection inside a structured paper under limited compute?

## Planned synthesis structure

1. Scientific paper QA and evidence supervision.
2. Retrieval and RAG foundations.
3. Adaptive and iterative retrieval.
4. Long-context use and over-reading.
5. Cost-aware routing and constrained tool use.
6. Gap, design choice, and limits of novelty.

## Verification rules

- Record an exact support location for each non-trivial claim.
- Prefer ACL Anthology, PMLR, OpenReview, journal, publisher, dataset-card, or official project pages.
- Verify DOI values against the publisher or Crossref/DBLP; encode DOI as `doi` and/or `url = {https://doi.org/...}`.
- Do not cite a survey as evidence for a primary method's own results when the original paper is available.
- Distinguish what a paper demonstrates from what this dissertation infers.

