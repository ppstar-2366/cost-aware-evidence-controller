# 实验文档索引

本目录保存实验协议、结果汇总、完整性检查和复现说明。正式结论以完整 QASPER 测试集的冻结检索实验和预先固定的生成样本为准；Validation50 文档只记录方法开发过程。

## 主要检索评价

1. [TEST_EVALUATION_PROTOCOL.md](TEST_EVALUATION_PROTOCOL.md)：测试集评价前固定的方法、基线、指标和重采样设计。
2. [TEST416_RESULTS.md](TEST416_RESULTS.md)：416篇论文、1,451个问题的主要结果和论文级配对区间。
3. [SUPPLEMENTARY_EXPERIMENT_PROTOCOL.md](SUPPLEMENTARY_EXPERIMENT_PROTOCOL.md)：预算匹配对照、控制器行为分析与生成实验的预定协议。
4. [SUPPLEMENTARY_RETRIEVAL_RESULTS.md](SUPPLEMENTARY_RETRIEVAL_RESULTS.md)：逐问题预算匹配、参考点与分支行为结果。

## 生成评价

1. [GENERATION_SMOKE_GATE.md](GENERATION_SMOKE_GATE.md)：输出长度、提示词去重和完整性检查记录。
2. [TEST_GENERATION_RESULTS.md](TEST_GENERATION_RESULTS.md)：53篇论文、201个问题的冻结生成结果、实际 token 数和配对区间。

## 复现与数据说明

- [REPRODUCTION_GUIDE_ZH.md](REPRODUCTION_GUIDE_ZH.md)：Windows 和 macOS 环境下的命令与运行顺序。
- [DATA_DICTIONARY_ZH.md](DATA_DICTIONARY_ZH.md)：源码、JSONL、CSV 和审计文件的字段定义。
- [FIGURE_GUIDE.md](FIGURE_GUIDE.md)：图文件、数据来源、可访问性设计和解释边界。

## 机器可读材料

- outputs/test416/：主要检索汇总、bootstrap 区间、错误分析和 SHA-256 清单。
- outputs/supplementary/：预算匹配、行为分析、生成结果和完整性审计。
- outputs/figures/：矢量 PDF、400 dpi PNG 及数据来源和输出哈希。
- experiment_audit.json、experiment_results_overview.csv 与 file_manifest_sha256.csv：Validation50 开发归档的机器可读检查。

QASPER 完整测试集、本地模型、提示词、生成原始记录和体积较大的逐问题检索 JSONL 文件没有提交到 Git。相应协议和清单保留了它们的生成方法、文件大小与 SHA-256 标识。
