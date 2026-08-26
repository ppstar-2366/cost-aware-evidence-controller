# 毕设实验档案索引

本目录是“Cost-Aware Evidence Controller for Scientific QA”项目的完整交接档案。它的目标是：即使原聊天记录丢失、换到另一台机器，也能从项目文件本身还原已完成的工作、实验设计、运行参数、数据含义、最终结果和当前局限。

## 建议阅读顺序

1. [TEST416_RESULTS.md](TEST416_RESULTS.md)：完整官方 test split 的冻结检索主结果与 paired bootstrap 解释。
2. [TEST_EVALUATION_PROTOCOL.md](TEST_EVALUATION_PROTOCOL.md)：主 test 评估在观察结果前固定的协议与完成记录。
3. [EXPERIMENT_GAP_AUDIT_ZH.md](EXPERIMENT_GAP_AUDIT_ZH.md)：提交前仍应补充的实验、优先级和不建议扩展的范围。
4. [SUPPLEMENTARY_EXPERIMENT_PROTOCOL.md](SUPPLEMENTARY_EXPERIMENT_PROTOCOL.md)：新增检索、机制对照、行为分析和 test 生成在运行前冻结的方案。
5. [SUPPLEMENTARY_RETRIEVAL_RESULTS.md](SUPPLEMENTARY_RETRIEVAL_RESULTS.md)：预算匹配机制对照、参考点和控制器行为分析结果。
6. [GENERATION_SMOKE_GATE.md](GENERATION_SMOKE_GATE.md)：冻结 test 生成样本、prompt 去重和两轮 completion gate 的完整记录。
7. [TEST_GENERATION_RESULTS.md](TEST_GENERATION_RESULTS.md)：冻结的 53-paper / 201-question test 生成结果、paired bootstrap 与结论边界。
8. [THESIS_FIGURE_GUIDE.md](THESIS_FIGURE_GUIDE.md)：论文图表、caption、可访问性与解释限制。
9. [THESIS_EVIDENCE_MAP_ZH.md](THESIS_EVIDENCE_MAP_ZH.md)：每项论文主张对应的数据、允许表述与禁止过度结论。
10. [EXPERIMENT_ARCHIVE_ZH.md](EXPERIMENT_ARCHIVE_ZH.md)：Validation50 开发过程、历史调试和生成实验归档。
11. [REPRODUCTION_GUIDE_ZH.md](REPRODUCTION_GUIDE_ZH.md)：从环境检查到重新运行全部实验的命令级手册。
12. [DATA_DICTIONARY_ZH.md](DATA_DICTIONARY_ZH.md)：每个源码、JSONL、CSV 文件及字段的含义。
13. [THESIS_WRITING_MATERIAL_ZH.md](THESIS_WRITING_MATERIAL_ZH.md)：毕业论文实验章节可直接使用的结构、表格和讨论要点。
14. [RESEARCH_REFLECTIONS_AND_CONCLUSIONS_ZH.md](RESEARCH_REFLECTIONS_AND_CONCLUSIONS_ZH.md)：实验感悟、研究结论、摘要结果句和未来工作。
15. [environment_snapshot.txt](environment_snapshot.txt)：早期本地生成实验的软件、模型和硬件快照。

## 机器可读档案

- [experiment_audit.json](experiment_audit.json)：从现有原始输出重新统计得到的完整审计结果。
- [experiment_results_overview.csv](experiment_results_overview.csv)：可直接用 Excel 打开的检索与生成结果总表。
- [file_manifest_sha256.csv](file_manifest_sha256.csv)：项目关键文件的大小、修改时间与 SHA-256 校验值。

## 当前完成状态

- 官方 QASPER test416 冻结检索：已完成，9 种方法各 1,451 条。
- Paper-level paired bootstrap：已完成，5,000 次，seed=42。
- Test 输出对齐与 SHA-256 审计：已通过。
- 补充检索参考点和两个预算匹配对照：已完成，各 1,451 条。
- ControllerV3 行为与问题级预算分布分析：已完成。
- 补充实验完整性、预算匹配与 SHA-256 审计：已通过。
- Test 生成样本与 prompt 去重：已冻结，53 篇 / 201 问 / 608 个 unique prompts。
- 20 问 test 生成 smoke gate：256-token 配置已通过，67/67 unique calls 成功。
- 冻结 test-sample 生成：608/608 unique calls 完整成功，0 failure、0 length stop。
- Test-sample Answer F1：ControllerV3 0.3280，BM25 top-7 0.3278；paired 差值
  +0.0002，95% CI [−0.0313, +0.0312]。
- 生成完整性、实际 token、去重节省和 SHA-256 审计：已通过。
- 论文结果图：4 张，均已输出矢量 PDF 和 400 dpi RGB PNG。
- 数据预处理：已完成。
- BM25 top-1/3/5/10/20：已完成，每种方法 156 条。
- ControllerV3：已完成，156 条。
- ControllerV3 去除章节扩展的消融实验：已完成，156 条。
- 阈值 0.5 的检索质量、成本和效率评估：已完成。
- ControllerV3 错误分析：已完成，覆盖 151 个具有标注证据的问题。
- Validation50 本地 Ollama 生成归档：4 种方法各 156 条，共 624 条，全部成功。
- Validation50 答案 F1/EM 与历史完整性审计：已归档。

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

注意：156-question Ollama 结果属于 Validation50 开发归档；终期下游证据应使用
[TEST_GENERATION_RESULTS.md](TEST_GENERATION_RESULTS.md) 的冻结 test sample，并同时
保留该文件关于“补充样本而非全量重新 untouched split”的限制。

档案核验日期：2026-08-27（Asia/Shanghai）。
