# 论文主张—实验数据证据映射

本文件用于解决论文写作中最常见的问题：某句话应该引用哪个实验文件、可以说到什么程度、不能说什么。每项主张都应能追溯到逐问题数据或正式汇总。

> **2026-08-27 更新：** 本文件原有第 1–13 节记录 Validation50 开发归档，
> 不能再称为独立“正式验证”。论文检索主结果必须优先使用下方 test416 映射；
> 下游主证据使用冻结的 test generation sample；Validation50 仅用于开发过程、
> prompt 试验和补充诊断。

## 0. 官方 test416 主结果映射

| 可写主张 | 数值或边界 | 正式证据 |
| --- | --- | --- |
| 完整官方 test split | 416 papers / 1,451 questions / 1,352 questions with gold evidence | `outputs/test416/test416_audit.json` |
| ControllerV3 主结果 | Recall 0.7099；Hit 0.8706；1,638 estimated tokens | `outputs/test416/test416_method_comparison_threshold05.csv` |
| 成本匹配 top-7 | Recall 0.7059；Hit 0.8624；1,629 estimated tokens | 同上 |
| Controller − top-7 Recall | +0.0040，95% paired CI [-0.0118, +0.0184] | `outputs/test416/test416_bootstrap_paired_differences.csv` |
| Controller − top-7 Hit | +0.0081，95% paired CI [-0.0044, +0.0210] | 同上 |
| 完整 − 无章节 Recall | +0.0220，95% paired CI [+0.0129, +0.0310] | 同上 |
| 完整 − 无章节 Hit | +0.0148，95% paired CI [+0.0046, +0.0255] | 同上 |
| 完整 − 无章节成本 | +104.0 estimated tokens，95% paired CI [+91.1, +117.1] | 同上 |
| 完整 − 同单元数通用扩展 Recall | +0.0027，95% paired CI [-0.0060, +0.0110] | `outputs/supplementary/test416_supplementary_bootstrap_paired_differences.csv` |
| 完整 − 同单元数通用扩展 Hit | +0.0067，95% paired CI [-0.0015, +0.0153] | 同上 |
| 完整 − 近似同 token 通用扩展 Recall | +0.0035，95% paired CI [-0.0051, +0.0118] | 同上 |

允许写：

> 在完整 QASPER test split 上，ControllerV3 与成本匹配的 BM25 top-7
> 具有接近的平均检索质量和估算成本；paired bootstrap 区间未显示清晰差异。

> 章节扩展相对低成本 no-section 版本提高了覆盖指标，但预算匹配补充分析未显示
> 章节定向相对通用 BM25 扩展具有清晰的独立检索收益。因此，原消融中的提升不能
> 可靠归因于章节定向，而更可能主要来自增加证据预算。

不能写：

> ControllerV3 显著优于 BM25 top-7。

> ControllerV3 与 top-7 已被统计证明等价。

> 章节感知在相同预算下优于普通 BM25 扩展。

预算匹配对照已经完成；其置信区间跨零，因而最后一句目前没有数据支持。该分析在
主 test 结果已知后固定，应标为 supplementary mechanism analysis，而非预注册的
主假设检验。完整解释见 `docs/SUPPLEMENTARY_RETRIEVAL_RESULTS.md`。

### 0.1 冻结 test generation sample 映射

| 可写主张 | 数值或边界 | 正式证据 |
| --- | --- | --- |
| 样本与调用 | 53 papers / 201 questions / 804 method rows / 608 unique prompts | `outputs/supplementary/generation/test_generation_integrity_audit.json` |
| ControllerV3 Answer F1 | 0.3280；95% CI [0.2756, 0.3850] | `outputs/supplementary/generation/test_generation_answer_bootstrap_method_cis.csv` |
| BM25 top-7 Answer F1 | 0.3278；95% CI [0.2710, 0.3875] | 同上 |
| Controller − top-7 F1 | +0.0002；95% paired CI [−0.0313, +0.0312] | `outputs/supplementary/generation/test_generation_answer_bootstrap_paired.csv` |
| Controller − top-8 F1 | −0.0188；95% paired CI [−0.0502, +0.0134] | 同上 |
| Controller − no-section F1 | +0.0143；95% paired CI [−0.0083, +0.0385] | 同上 |
| Controller − no-section actual prompt tokens | +128.58；95% paired CI [+94.02, +165.62] | 同上 |
| 完整性 | 608/608 complete；0 failure；0 length stop；max prompt 3,796/8,192 | `outputs/supplementary/generation/test_generation_integrity_audit.json` |

允许写：

> 在冻结的 201-question paper-cluster sample 和固定 Qwen2.5-3B 生成设置下，
> ControllerV3 与 BM25 top-7 的 Answer F1 点估计几乎相同，paired interval 未显示
> 清晰差异。

不能把区间跨零写成统计等价，也不能称为全 1,451 问的生成评估。由于 test split
已先用于检索主实验，该生成结果必须称为 frozen supplementary test sample，而非
新获得的 untouched evaluation。完整解释见 `docs/TEST_GENERATION_RESULTS.md`。

## 1. 数据规模主张

| 可写主张 | 数值 | 原始证据 | 核验位置 |
| --- | --- | --- | --- |
| Validation50 开发分析包含 50 篇论文 | 50 | `data/processed/qasper_validation_50.jsonl` | `experiment_audit.json → datasets.validation_50.papers` |
| Validation50 开发分析包含 156 个问题 | 156 | 同上 | `datasets.validation_50.questions` |
| 有金证据的问题 | 151 | 同上 raw answers | `questions_with_gold_evidence` |
| 金证据片段总数 | 395 | 同上 raw answers | `total_gold_evidence_spans` |
| 验证证据单元总数 | 1,574 | 同上 | `evidence_units` |

推荐措辞：

> 开发分析使用 QASPER validation split 前 50 篇论文，共 156 个问题；其中 151 个问题具有标注证据，共包含 395 条去重金证据片段。

不能写成“随机选取 50 篇”，因为代码使用前 50 篇。

## 2. 固定 top-k 成本趋势

| 主张 | 关键数据 | 正式文件 |
| --- | --- | --- |
| k 增大时召回上升 | 0.2304 → 0.9519 | `outputs/validation50_method_comparison_threshold05.csv` |
| k 增大时成本上升 | 216 → 4,144 estimated tokens | 同上 |
| 边际单位成本收益下降 | Recall/1k 1.0667 → 0.2297 | 同上 |

允许写：

> 增大固定检索预算提高证据覆盖，但同时显著增加阅读成本，并表现出单位成本覆盖收益下降。

不建议写：

> BM25 top-20 效果最差。

top-20 的召回最好，只是成本高。

## 3. ControllerV3 的位置

| 指标 | top-5 | ControllerV3 | top-10 |
| --- | ---: | ---: | ---: |
| Recall | 0.5646 | 0.7063 | 0.7772 |
| Hit Rate | 0.7748 | 0.8675 | 0.9007 |
| Estimated Tokens | 1,156 | 1,640 | 2,322 |

允许写：

> ControllerV3 在质量和成本上均位于 BM25 top-5 与 top-10 之间，构成一个动态、可解释的中间预算点。

> 相对 top-10，ControllerV3 减少约 29.4% 的估算 token，Recall 低 7.09 个百分点。

不能写：

> ControllerV3 在检索质量上超过 BM25 top-10。

> ControllerV3 是单位成本效率最高的方法。

证据文件：

- 汇总：`outputs/validation50_method_comparison_threshold05.csv`；
- 逐问题：`outputs/validation50_controller_v3.jsonl`；
- 动作统计：`docs/experiment_audit.json → retrieval.ControllerV3_diagnostics`。

## 4. 章节扩展贡献

| 指标 | 无章节扩展 | 完整版本 | 变化 |
| --- | ---: | ---: | ---: |
| Recall | 0.6759 | 0.7063 | +0.0304 |
| Hit Rate | 0.8344 | 0.8675 | +0.0331 |
| Avg. Best Overlap | 0.6993 | 0.7231 | +0.0238 |
| Estimated Tokens | 1,543 | 1,640 | +97 |
| Recall/1k | 0.4380 | 0.4307 | -0.0073 |

允许写：

> 章节感知扩展以约 97 个额外估算 token 为代价，提高了证据召回、问题命中率和平均覆盖程度。

不建议只写“章节扩展提高效率”，因为 Recall/1k 略有下降。更准确的是“提高质量，但增加成本”。

证据文件：

- `outputs/validation50_controller_v3.jsonl`；
- `outputs/validation50_controller_v3_no_section.jsonl`；
- `outputs/validation50_method_comparison_threshold05.csv`。

## 5. 下游生成结论

| 方法 | F1 | EM | 成功数 |
| --- | ---: | ---: | ---: |
| BM25 top-5 | 0.259133 | 0.121795 | 156/156 |
| BM25 top-10 | 0.262938 | 0.128205 | 156/156 |
| BM25 top-20 | 0.257749 | 0.121795 | 156/156 |
| ControllerV3 | 0.257732 | 0.121795 | 156/156 |

允许写：

> 在当前本地 3B 生成器和固定 prompt 预算下，ControllerV3 的答案 F1/EM 与固定 top-k 基线总体接近。

不能写：

> ControllerV3 显著优于 BM25。

> top-20 的额外证据降低了答案质量。

原因：没有显著性检验，而且 top-10 与 top-20 的实际 prompt 全部相同。

证据文件：

- 正式汇总：`outputs/ollama_answer_summary_validation50.csv`；
- 逐问题得分：`outputs/ollama_answer_scores_validation50.csv`；
- 原始回答：`outputs/ollama_generations_validation50.jsonl`；
- paired comparison：`docs/experiment_audit.json → answer_generation`。

## 6. Prompt 上限主张

| Prompt 对 | 完全相同 |
| --- | ---: |
| top-10 vs top-20 | 156/156 |
| top-5 vs top-10 | 121/156 |
| Controller vs top-10 | 134/156 |

允许写：

> 6000 字符证据上限压缩了不同检索方法的实际模型输入差异，因此生成实验属于固定上下文预算下的下游验证。

证据位置：`docs/experiment_audit.json → generation_prompts.paired_prompt_comparisons`。

## 7. 推理非完全确定性

事实：top-10 与 top-20 prompt 156/156 相同，但生成答案只有 147/156 相同，9 对不同。

允许写：

> 尽管设置 temperature=0 和 seed=42，跨时段续跑的本地推理仍未实现逐字符完全确定，因此相同 prompt 的微小评分差异不应解释为检索效应。

证据位置：`docs/experiment_audit.json → answer_generation.paired_generated_answer_comparisons`。

## 8. 错误分析主张

| 类别 | 数量 |
| --- | ---: |
| success | 131 |
| controller_selection_failure | 10 |
| retrieval_or_gold_mapping_failure | 3 |
| figure_selection_failure | 2 |
| data_evidence_selection_failure | 2 |
| definition_selection_failure | 1 |
| result_evidence_selection_failure | 1 |
| missing_figure_failure | 1 |

允许写：

> 20 个 Controller 未命中问题中，一般控制器选择失败占 50%，数据和图示证据选择是其余主要可识别问题。

注意：这些类别由启发式规则自动生成，不是多人独立人工标注。论文中应称为“诊断性错误分类”。

证据文件：`outputs/error_analysis_controller_v3_validation50.csv`。

## 9. 可解释性主张

允许写：

> ControllerV3 为每个问题保存问题标签、动作序列、每项动作新增的单元数和停止原因，并在每个证据单元上记录 `selected_by`，因此其选择过程可以逐问题追踪。

证据字段：

- `outputs/validation50_controller_v3.jsonl → question_type`；
- `actions[].action`；
- `actions[].added_units`；
- `actions[].reason`；
- `retrieved_units[].selected_by`。

不要把“可追踪”直接等同于“因果解释”或“模型内部可解释性”。这里的解释来自显式规则和动作日志。

## 10. 低资源与可复现性主张

允许写：

> 全部回答生成使用本地 Qwen2.5-3B，在约 8 GB 内存和集成显卡机器上通过断点续跑完成，不依赖付费在线 API。

证据：

- `docs/environment_snapshot.txt`；
- `outputs/ollama_generations_validation50.jsonl` 的模型和 created_at；
- `src/run_ollama_generation.py` 的续跑逻辑。

不能用 wall-time 证明“方法运行更快”，因为执行跨多次中断且缓存条件不一致。

## 11. 局限主张与证据

| 局限 | 事实依据 | 应放章节 |
| --- | --- | --- |
| 样本较小 | 50 papers / 156 questions | 有效性威胁 |
| 非随机前 N 篇 | `split.select(range(...))` | 数据设置 |
| validation 同时参与规则改进与报告 | Controller 注释和开发过程 | 内部有效性 |
| 词法 overlap 是代理 | `retrieval.py` | 指标局限 |
| token 成本为 word×1.3 | `common.py` | 成本定义 |
| prompt 有 6000 字符上限 | `build_generation_prompts.py` | 生成设置 |
| 无显著性检验 | 当前输出文件 | 有效性威胁 |
| 无 dense baseline | 当前方法列表 | 外部比较局限 |
| wall-time 不可比 | 中断恢复记录 | 实现局限 |

主动披露这些内容不会削弱论文，反而说明对实验边界有清楚认识。

## 12. 表格和图片的数据来源

| 论文内容 | 建议来源 |
| --- | --- |
| 终期检索主表 | `outputs/test416/test416_method_comparison_threshold05.csv` |
| 终期 paired 检索差值 | `outputs/test416/test416_bootstrap_paired_differences.csv` |
| 终期生成主表 | `outputs/supplementary/generation/test_generation_answer_summary.csv` |
| 终期 paired 生成差值 | `outputs/supplementary/generation/test_generation_answer_bootstrap_paired.csv` |
| 终期结果图 | `outputs/figures/*.pdf` 与 `figure_manifest.json` |
| 检索主表 | `outputs/validation50_method_comparison_threshold05.csv` |
| 消融表 | 同上两行 Controller |
| 生成主表 | `outputs/ollama_answer_summary_validation50.csv` |
| 质量—成本散点图 | `docs/experiment_results_overview.csv` |
| Controller 动作图 | `experiment_audit.json → ControllerV3_diagnostics.action_counts` |
| 错误类别图 | `experiment_audit.json → error_analysis.failure_category_counts` |
| 典型错误案例 | `outputs/error_analysis_controller_v3_validation50.csv` |
| F1 分布 | `experiment_audit.json → answer_score_distributions` |

## 13. 写作时的最终核对方法

每写一个定量句子，检查四件事：

1. 数值来自哪个文件；
2. 分母是 151、156、395 还是 624；
3. 指标是估算 token 还是 Ollama 实际 prompt token；
4. 该句是在描述相关结果，还是错误地声称显著性或因果关系。

如果无法回答其中任何一项，应回到 `experiment_audit.json` 或逐问题输出核验后再写。
