# Imperial Report Requirements Audit

Source checked: Department of Computing **Report Writing** and **Declarations** pages, accessed 27 August 2026, plus the user-provided `Report+Writing.doc` export.

| Requirement | Implementation | Status |
| --- | --- | --- |
| UK English | `babel` set to `british`; prose uses UK spellings | pass (manual recheck still required) |
| A4 | `a4paper` document option and geometry | pass |
| approximately 2.5 cm margins | `geometry` uses `margin=2.5cm` | pass |
| minimum 11 pt | document class uses 11 pt | pass |
| maximum 60 content pages | manuscript targets 40--50; final compiled count pending | pending compile |
| abstract at most one page | concise abstract with concrete results | pending compile |
| no abstract citations | no `\\cite` in abstract | pass |
| Vancouver references | numeric citation order through `natbib`/`unsrtnat` | pending rendered check |
| complete references | 21 cited entries; DOI link used where verified | pass for current citations |
| Declarations after References, before Appendices | included in `main.tex` in required position | pass |
| generative-AI declaration | tool, provider, URL, uses, verification, and responsibility disclosed | author review required |
| ethical considerations | public dataset, no participants/private data, risks and mitigations stated | author review required |
| sustainability | local low-resource model, deduplication, caching and resumability stated | author review required |
| data/materials availability | repository and local-large-file boundary stated | author review required |
| source code excluded from report | no listings; repository referenced | pass |
| introduction/related work/body/evaluation/conclusion | explicit chapters included | pass |
| figures break up long text | one system diagram and four empirical figures | pass |
| citations not stranded at line starts | non-breaking spaces used before all `\\cite{}` calls | pass |
| DOI hyperlinks requested by second marker | DOI URLs are clickable through `hyperref` | pending rendered check |

