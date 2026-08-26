# 后续实验缺口审计与执行优先级

审计日期：2026-08-27（Asia/Shanghai）

## 1. 审计目的与边界

本审计比较中期报告承诺、当前 ControllerV3 实现和已经完成的 QASPER
test416 结果，回答三个问题：哪些证据仍不足以支撑终期论文主张，哪些补充实验
具有最高信息增益，以及哪些原计划不应在当前阶段仓促实现。

当前官方 test split 已经用于一次冻结的主检索评估。后续分析不得修改
ControllerV3 后再次把同一 test split 描述为未接触的 held-out evaluation。新增
test 分析必须标为预先写明方案后的 supplementary analysis；探索性子组结果不得
替代主结果。

## 2. 已经充分覆盖的部分

以下内容无需为了“增加实验数量”而重复：

- 完整官方 QASPER test split：416 篇论文、1,451 个问题；
- BM25 top-1/3/5/7/8/10/20 质量—成本曲线；
- 与 ControllerV3 成本几乎相同的 BM25 top-7 主比较；
- ControllerV3 无章节扩展消融；
- overlap threshold 0.3/0.5/0.7 敏感性分析；
- 5,000 次 paper-level paired bootstrap 和 95% 区间；
- 输出对齐、重复键、缺失键和 SHA-256 完整性审计。

现有主结果支持的最强表述是：ControllerV3 与 BM25 top-7 在平均估算成本和
总体检索质量上接近，主比较区间未显示清晰差异。它不支持“ControllerV3 明确
优于成本匹配固定预算”的结论。

## 3. 提交前必须补充：P0

### P0-A：独立的下游答案生成评估

**目的。** 中期报告把“完整 evidence-grounded QA pipeline”列为最低成功标准，
但当前生成实验只在参与规则开发的 Validation50 上完成，而且 6,000 字符上限
使许多方法形成相同 prompt。若终期论文要讨论 Answer F1、EM 或最终 QA 效用，
必须补一个与当前 test 检索结果配套的生成实验。

**冻结方案。**

- 从 test416 按论文随机抽样完整 paper clusters，seed=42，累积到至少 200 个问题；
- 比较 ControllerV3、BM25 top-7、BM25 top-8 和 ControllerV3-no-section；
- 使用同一 `qwen2.5:3b`、prompt 模板、temperature=0、seed=42、num_ctx=8192；
- 取消会使方法输入塌缩的 6,000 字符硬截断，改为显式上下文预算并记录 Ollama
  实际 `prompt_eval_count`；
- 对完全相同的 prompt 只生成一次，再把同一回答复用于对应方法，消除相同输入
  因重复推理非确定性产生的伪差异；
- 报告官方风格 Answer F1、Exact Match、按答案类型的 F1、unanswerable accuracy、
  实际输入/输出 tokens 和成功率；
- 对方法差值做 5,000 次 paper-level paired bootstrap；
- 先完成 20 个问题的 smoke run，检查 prompt 去重、答案解析和 token 记录，再运行
  冻结样本；不得根据 smoke/test 答案修改 ControllerV3。

**完成判据。** 每种方法覆盖完全相同的问题；相同 prompt 的生成答案完全相同；
主结果同时报告效果差值和实际 token 差值，而不只报告各方法均值。

### P0-B：章节扩展的预算匹配对照

**状态：已完成并通过审计。** 完整结果见
`docs/SUPPLEMENTARY_RETRIEVAL_RESULTS.md`。ControllerV3 相对严格同单元数通用
扩展的 Recall 差值为 +0.0027，95% paired CI [-0.0060, +0.0110]；当前数据没有
证明章节定向具有独立的总体检索收益。

**目的。** 当前 full-vs-no-section 消融同时改变了证据选择策略和平均成本
（约 +104 estimated tokens）。因此它证明“增加章节扩展后覆盖上升”，但尚不能
证明收益来自章节定向，而不是单纯多读证据。

**方案。** 新增 `generic-budget-matched expansion`：沿用 no-section 版本的证据，
再按普通 BM25 顺序补充未选单元，直到逐问题匹配完整 ControllerV3 的证据单元数
或 token 预算。该对照不得使用 gold evidence。比较：

- ControllerV3 vs generic-budget-matched；
- Evidence Recall、Hit Rate、Best Overlap、实际匹配成本；
- 5,000 次 paper-level paired bootstrap；
- 单元数匹配和 token 匹配均需审计并报告残余差异。

这项实验比再做多个“删除一个动作”的非预算匹配消融更能回答机制问题。

### P0-C：Controller 可变预算与行为分布

**状态：已完成并通过审计。** ControllerV3 平均检索 7.76 个单元（SD 2.24），
相对 top-7 在 26.1% / 29.6% / 44.3% 的问题上分别使用更少 / 相同 / 更多估算
token，证明实现确实重新分配问题级预算，但平均预算并未明显下降。

**目的。** 平均成本相近并不能证明控制器确实分配了可变预算。论文中的
“question-aware variable-budget”主张需要行为证据。

**方案。** 对 test416 生成纯描述性分析：

- retrieved units 和 estimated tokens 的 mean、SD、median、IQR、P10/P90；
- ControllerV3 相对 top-7 逐问题更少、相同、更多预算的比例；
- 互斥决策路径：definition、result/data、method/complex、default；
- 每条路径的问题数、金证据问题数、Recall、Hit Rate、tokens 和动作分布；
- 图表/表格动作的触发次数与实际新增单元数；
- 该子组分析标为 descriptive/exploratory，因为 test 主结果完成后才制定。

由于问题类别本身驱动规则，动作频率只能证明实现按规则运行，不能单独证明规则
有效。有效性仍需依靠预算匹配的 paired outcome comparison。

### P0-D：补齐中期报告预先列出的低/高成本参考点

**状态：已完成并通过审计。** Abstract-only Recall 为 0.1063、平均约 178
estimated tokens；Read-all Recall 为 0.9973、平均约 5,130 estimated tokens。

在不修改 ControllerV3 的前提下，补充 retrieval-only 的：

- Abstract-only；
- Read-all retrievable evidence。

二者计算成本很低，并且在中期报告中已明确列为最终 baseline。它们应标为
supplementary reference points，不得回头改变主比较或阈值。Read-all 只用于展示
覆盖上界和成本，不建议进入本地 3B 生成实验。

## 4. 高收益但非必需：P1

### P1-A：表格读取消融

若 P0 完成后仍有时间，可比较完整 ControllerV3 与 no-table 版本。必须同时报告
成本变化，并优先加入预算匹配普通证据的对照。figure-caption 消融预计样本极少，
只适合作为描述性附录，不应占据主表。

### P1-B：固定 dense retrieval baseline

可预先固定一个轻量公开 encoder（例如 `BAAI/bge-small-en-v1.5`）及 top-k，不在
test 上选择模型或参数，再报告同一 overlap/cost 指标。这能说明 BM25 词法候选池
是否是主要瓶颈，但它不能直接证明 ControllerV3 在 dense retrieval 上仍有效，
因为当前控制器内部扩展仍使用 BM25。若时间有限，应先完成 P0，而不是优先加入
dense baseline。

### P1-C：人工核验错误分析

当前错误类别由启发式程序生成。可以从 test failures 中按固定 seed 抽取 30–50 个
案例，用预先定义的 retrieval/controller/mapping/generation/budget rubric 单人复核。
结果应称为 qualitative audit；没有第二标注者时不得声称标注可靠性或一致性。

## 5. 当前阶段不建议实现：P2

### P2-A：ControllerV4 或真正 evidence-sufficiency dynamic stopping

当前没有未接触的官方 split 可供“开发 V4 后再做独立终评”。在已经观察 test
结果后重新设计充分性分数、SearchMore 和 Stop，再在同一 test 上报告，会削弱而
不是增强可信度。终期论文应准确把 V3 描述为规则式、问题感知、可变预算控制器，
并把真正动态停止列为 future work。

### P2-B：全量多方法 test generation

在冻结的 cluster sample 已能回答主要下游问题时，直接运行 1,451×4 次本地生成的
边际信息增益有限。只有在样本实验稳定、时间充足且实际 token/prompt 审计无问题
时，才扩展到全量。

### P2-C：为了满足中期措辞而临时构造“Evidence Precision/F1”

QASPER 官方 Evidence F1 在原始段落集合上计算，而当前项目把章节重新切成重叠
chunks，预测单元与官方段落不一一对应。不能把“命中 gold span 的 retrieved-unit
比例”和“gold-span recall”混合后称为官方 Evidence F1。终期论文应明确说明当前
使用的是 chunk-to-gold token-overlap Recall/Hit proxy。若要报告官方 Evidence F1，
需要保留原始 paragraph IDs、重新定义预测证据单元并重跑整套方法；当前截止阶段
不建议进行这项架构级改动。

## 6. 推荐执行顺序与预估成本

| 顺序 | 工作 | 计算成本 | 对论文可信度的增益 |
|---|---|---:|---|
| 1 | 固定下游生成协议、修复 prompt 去重与 token 审计 | 低（开发） | 极高（进行中） |
| 2 | 200+ 问题 cluster-sampled generation | 中等，约 800 个方法—问题记录，实际 unique prompts 更少 | 极高（待完成） |
| 3 | 章节扩展预算匹配对照 | 低，纯检索 | 已完成 |
| 4 | 可变预算/动作/决策路径分析 | 低，离线统计 | 已完成 |
| 5 | Abstract-only 与 Read-all | 很低，纯检索 | 已完成 |
| 6 | no-table 或 dense baseline | 中等 | 中等 |
| 7 | ControllerV4、全量四方法生成 | 高 | 当前阶段风险大于收益 |

## 7. 论文主张应同步收敛

- 使用“rule-based, question-aware variable-budget evidence controller”；
- 不使用“evidence-sufficiency-based dynamic stopping”描述当前 Stop；
- 不把主比较区间跨零写成“equivalent”或“significantly better”；
- 把 test 主检索结果、后续 supplementary 分析和 Validation50 开发结果分开；
- 把估算 `words × 1.3` 与 Ollama 实际 tokenizer counts 分开；
- 把自动错误分类称为 diagnostic heuristic，而不是人工 gold failure taxonomy。

本计划的核心不是增加方法数量，而是补齐三条证据链：最终答案是否仍可用、章节
定向是否超越单纯增加预算、控制器是否真的以可追踪方式分配不同预算。
