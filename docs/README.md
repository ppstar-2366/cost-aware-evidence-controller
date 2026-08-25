# 毕设实验档案索引

本目录是“Cost-Aware Evidence Controller for Scientific QA”项目的完整交接档案。它的目标是：即使原聊天记录丢失、换到另一台机器，也能从项目文件本身还原已完成的工作、实验设计、运行参数、数据含义、最终结果和当前局限。

## 建议阅读顺序

1. [EXPERIMENT_ARCHIVE_ZH.md](EXPERIMENT_ARCHIVE_ZH.md)：完整工作记录、实验设计、全部结果、历史调试与结论边界。
2. [REPRODUCTION_GUIDE_ZH.md](REPRODUCTION_GUIDE_ZH.md)：从环境检查到重新运行全部实验的命令级手册。
3. [DATA_DICTIONARY_ZH.md](DATA_DICTIONARY_ZH.md)：每个源码、JSONL、CSV 文件及字段的含义。
4. [THESIS_WRITING_MATERIAL_ZH.md](THESIS_WRITING_MATERIAL_ZH.md)：毕业论文实验章节可直接使用的结构、表格和讨论要点。
5. [RESEARCH_REFLECTIONS_AND_CONCLUSIONS_ZH.md](RESEARCH_REFLECTIONS_AND_CONCLUSIONS_ZH.md)：实验感悟、研究结论、摘要结果句和未来工作。
6. [THESIS_EVIDENCE_MAP_ZH.md](THESIS_EVIDENCE_MAP_ZH.md)：每项论文主张对应的数据、允许表述与禁止过度结论。
7. [environment_snapshot.txt](environment_snapshot.txt)：完成最终实验时的软件、模型和硬件快照。

## 机器可读档案

- [experiment_audit.json](experiment_audit.json)：从现有原始输出重新统计得到的完整审计结果。
- [experiment_results_overview.csv](experiment_results_overview.csv)：可直接用 Excel 打开的检索与生成结果总表。
- [file_manifest_sha256.csv](file_manifest_sha256.csv)：项目关键文件的大小、修改时间与 SHA-256 校验值。

## 当前完成状态

- 数据预处理：已完成。
- BM25 top-1/3/5/10/20：已完成，每种方法 156 条。
- ControllerV3：已完成，156 条。
- ControllerV3 去除章节扩展的消融实验：已完成，156 条。
- 阈值 0.5 的检索质量、成本和效率评估：已完成。
- ControllerV3 错误分析：已完成，覆盖 151 个具有标注证据的问题。
- 本地 Ollama 回答生成：已完成，4 种方法各 156 条，共 624 条，全部成功。
- 答案 F1/EM 评估：已完成，共 624 条。
- 完整性审计与文件哈希：已完成。

## 迁移到另一台机器时

不要只复制 `docs/`。应复制整个 `cost_aware_evidence_controller` 文件夹，尤其保留：

- `src/`：实验实现；
- `data/processed/`：已处理的 QASPER 子集；
- `outputs/`：逐问题原始实验结果；
- `docs/`：本交接档案；
- `README.md` 与 `requirements.txt`。

复制后首先运行：

```powershell
.\.venv\Scripts\python.exe src\audit_experiments.py
```

如果新机器还没有 `.venv`，请先按 [REPRODUCTION_GUIDE_ZH.md](REPRODUCTION_GUIDE_ZH.md) 重建环境。审计脚本只读取现有实验数据并刷新档案，不会重新调用 Ollama，也不会覆盖原始检索或生成结果。

档案核验日期：2026-08-20（Asia/Shanghai）。
