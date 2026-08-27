# MSc Dissertation LaTeX Project

This directory contains the working final dissertation:

> **Question-Aware Variable-Budget Evidence Selection for Scientific Paper Question Answering**

The project follows the Imperial College Department of Computing report-writing guidance available on 27 August 2026:

- UK English;
- A4 paper, 11 pt text, 2.5 cm margins;
- maximum 60 content pages;
- numeric Vancouver-style references;
- abstract no longer than one page and containing no citations;
- required Declarations section after References and before Appendices;
- no source-code listings in the dissertation.

## Main files

- `main.tex`: document preamble and chapter order;
- `title/title.tex`: title page and project metadata;
- `frontmatter/`: abstract, acknowledgements, and required declarations;
- `chapters/`: dissertation chapters;
- `bibs/references.bib`: verified primary-source bibliography with DOI links where available;
- `figures/`: publication-ready experiment figures generated from archived CSV/JSON results;
- `appendix/appendix.tex`: reproducibility and supplementary material;
- `research/`: paper plan, review contract, source ledger, and claim--evidence matrix.

## Compilation

The intended engine is pdfLaTeX with BibTeX. Compile with:

```text
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

Overleaf should perform these passes automatically. The title page uses the Imperial template's `title/logo.eps` when that file is present and otherwise compiles without a logo.

## Claim discipline

Primary retrieval claims must trace to `outputs/test416/`. Supplementary mechanism and generation claims must be labelled as such and trace to `outputs/supplementary/`. Results from `validation50` are development evidence only.

Before submission, the author must personally review the Acknowledgements and Declarations, confirm the title/date/name formatting, check the current departmental generative-AI policy, and run the final PDF through Turnitin if desired.

