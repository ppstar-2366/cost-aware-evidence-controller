# 实验文档

这个目录放的是实验协议、结果摘要、完整性检查和复现命令。项目在 2026 年
6–8 月主要在本地开发和运行，主要实验结束后才将代码、小型结果文件和说明统一
整理到 GitHub。因此，文档中的日期表示对应协议、运行或检查的记录时间，Git
提交日期并不是完整的本地开发时间线。

正式检索结论来自完整 QASPER test split；Validation50 只用于方法开发和早期排查。

## 主要检索实验

- [TEST_EVALUATION_PROTOCOL.md](TEST_EVALUATION_PROTOCOL.md)：测试集运行前确定的方法、基线、指标和 bootstrap 设置。
- [TEST416_RESULTS.md](TEST416_RESULTS.md)：416 篇论文、1,451 个问题的检索结果和论文级配对区间。
- [SUPPLEMENTARY_EXPERIMENT_PROTOCOL.md](SUPPLEMENTARY_EXPERIMENT_PROTOCOL.md)：预先记录的预算匹配、控制器行为和生成实验设置。
- [SUPPLEMENTARY_RETRIEVAL_RESULTS.md](SUPPLEMENTARY_RETRIEVAL_RESULTS.md)：逐问题预算匹配、参考点和分支行为结果。

## 答案生成实验

- [GENERATION_SMOKE_GATE.md](GENERATION_SMOKE_GATE.md)：正式生成前对输出长度、prompt 去重和完整性的检查。
- [TEST_GENERATION_RESULTS.md](TEST_GENERATION_RESULTS.md)：53 篇论文、201 个问题的生成结果、实际 token 数和配对区间。

## 复现和文件说明

- [REPRODUCTION_GUIDE_ZH.md](REPRODUCTION_GUIDE_ZH.md)：Windows 和 macOS 下的环境、命令与运行顺序。
- [DATA_DICTIONARY_ZH.md](DATA_DICTIONARY_ZH.md)：源码、JSONL、CSV 和检查文件的字段。
- [FIGURE_GUIDE.md](FIGURE_GUIDE.md)：图片的数据来源、输出格式和阅读边界。

## 机器可读结果

- `outputs/test416/`：主要检索汇总、bootstrap 区间、错误分析和 SHA-256 清单。
- `outputs/supplementary/`：预算匹配、行为分析、生成结果和完整性检查。
- `outputs/figures/`：PDF、PNG 及其数据来源和输出哈希。
- `experiment_audit.json`、`experiment_results_overview.csv` 和
  `file_manifest_sha256.csv`：Validation50 开发实验的汇总检查。

完整 QASPER 测试数据、本地模型、完整 prompts、原始生成记录和大型逐问题
JSONL 没有上传。对应的文件大小和 SHA-256 值保留在各结果目录的 manifest 中。
