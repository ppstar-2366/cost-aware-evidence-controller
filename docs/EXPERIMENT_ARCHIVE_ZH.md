# 毕设实验完整档案

## 1. 档案用途与最终状态

项目名称：**Cost-Aware Evidence Controller for Scientific QA**。

研究任务：在 QASPER 科学论文问答数据上，研究一个轻量、可解释、问题感知的证据控制器，能否在少读取论文证据的情况下，保持较高的证据覆盖率，并支持本地小语言模型完成下游回答生成。

截至 2026-08-20，已保存并核验的正式实验包括：

- 100 篇训练论文和 50 篇验证论文的数据预处理；
- BM25 top-1、top-3、top-5、top-10、top-20 五组固定预算基线；
- 完整 ControllerV3；
- 去除 section-aware expansion 的 ControllerV3 消融实验；
- 检索质量、证据成本、成本效率评估；
- ControllerV3 逐问题错误分析；
- 4 组方法的本地 Ollama 下游回答生成；
- 624 条回答的 F1、Exact Match 和 token 统计；
- 完整性审计、字段清单与 SHA-256 文件校验。

正式生成实验共有 624 个唯一的“方法—问题”记录，4 种方法各 156 条，全部 `status=ok`，没有失败记录、重复记录或被后续记录覆盖的旧记录。

## 2. 实际完成的工作量

### 2.1 项目整理与工程化

原有分散脚本被整理为一个较清晰的流水线：

- `src/common.py`：统一 JSONL/CSV 读写、tokenize、参考答案与金证据提取；
- `src/retrieval.py`：统一 BM25、问题类型识别、检索评估和成本统计；
- `src/run_controller_v3.py`：保留最终 ControllerV3，且支持关闭章节扩展做消融；
- `src/run_retrieval_experiment.py`：一次运行所有 BM25、控制器、消融和错误分析；
- `src/build_generation_prompts.py`：统一生成下游问答提示词；
- `src/run_ollama_generation.py`：支持按方法运行、失败重试、断点续跑；
- `src/evaluate_generated_answers.py`：统一答案 F1/EM 评估；
- `src/audit_experiments.py`：最终新增的只读审计脚本，用于换机和论文提交前复核。

清理过的内容主要是安装/启动测试日志、后台进程试跑文件、旧的小规模探针结果和 Python 缓存。正式数据、正式检索结果、正式生成结果均已保留。被清理的临时文件不属于论文正式证据链，当前关键文件全部列入 `file_manifest_sha256.csv`。

### 2.2 本地模型环境

为了避免付费 API，并使实验可在同一模型上从测试阶段运行到最终阶段，安装并使用了本地 Ollama：

- Ollama 可执行文件：`D:\Ollama\ollama.exe`；
- 模型存储目录：`D:\OllamaModels`；
- Ollama 版本：0.30.10；
- 模型：`qwen2.5:3b`；
- 模型 ID：`357c53fb659c`；
- 模型磁盘大小：约 1.9 GB；
- API：`http://127.0.0.1:11434/api/generate`。

当时机器为 Intel Core i5-10210U、约 7.8 GB 内存、Intel UHD 集成显卡，无独立 NVIDIA GPU。因此完整生成速度较慢，并经历过锁屏、关机或前台任务中断。生成脚本通过读取已有输出中的 `(method, question_id)` 和 `status=ok` 实现安全续跑，最终没有丢失正式记录。

### 2.3 提示词调试与小规模试验

早期提示词对小型 3B 模型过于保守，模型频繁输出 “Not enough evidence.”。之后把任务明确改为“从给定证据中抽取最短正确答案”，要求优先复制证据中的词组，只有证据明显无关时才拒答。

改写提示词后曾进行每种方法 10 条的小规模诊断：

| 方法 | 诊断 F1 | 诊断 EM | 成功数 |
| --- | ---: | ---: | ---: |
| BM25_top5 | 0.182323 | 0 | 10/10 |
| BM25_top10 | 0.182323 | 0 | 10/10 |
| BM25_top20 | 0.182323 | 0 | 10/10 |
| ControllerV3 | 0.190016 | 0 | 10/10 |

这只是提示词可运行性诊断，不是正式论文结果。对应临时文件在最终清理时删除，正式结论必须引用后面的 156 问题全量结果。

## 3. 研究问题与可检验假设

主要研究问题：固定较大的 top-k 虽然能提高证据召回，但会增加需要读取的论文上下文；一个根据问题类型动态采取动作的轻量控制器，能否取得更合理的质量—成本平衡？

可检验假设：

- H1：随着 BM25 的 k 增大，证据召回率和问题命中率上升，但证据 token 成本显著增加。
- H2：ControllerV3 的召回和成本应位于 BM25 top-5 与 top-10 之间，形成可解释的中间预算点。
- H3：章节感知扩展应比去除章节扩展的消融版本取得更高召回与命中率。
- H4：ControllerV3 提供的较低成本证据能够让本地 3B 模型达到与固定 top-k 相近的答案 F1/EM。

现有结果支持 H1、H2、H3；H4 在当前受提示词字符上限影响的下游实验中得到“性能相近”的支持，但不能据此宣称 ControllerV3 在答案质量上显著优于 BM25。

## 4. 数据集与预处理

### 4.1 数据来源与抽样方式

数据由 Hugging Face `allenai/qasper` 加载。脚本直接选取各 split 的前 N 篇：

- train split 前 100 篇，保存为 `data/processed/qasper_train_100.jsonl`；
- validation split 前 50 篇，保存为 `data/processed/qasper_validation_50.jsonl`。

这不是随机抽样，代码没有设置数据抽样随机种子。训练子集只被处理并保留；最终控制器是规则系统，没有进行参数训练。正式指标全部来自 validation 前 50 篇。

### 4.2 预处理方法

1. 对字符串、列表、嵌套列表和字典字段做递归文本规范化，压缩多余空白。
2. 标题保存为 `title` unit，摘要保存为 `abstract` unit。
3. 每个正文 section 先合并段落，再按最多 250 个英文空格词切块，相邻块重叠 40 词。
4. 图表 caption 根据开头的 `Table`、`Figure` 或 `Fig.` 规则划分为 `table`、`figure_caption`；无法确定的保留为 `figure_table`。
5. 每个证据单元保存论文 ID、unit ID、unit type、section、正文位置、source ID、文本和 word count。
6. 每个问题保留 question ID、问题文本和 QASPER 原始答案结构。

### 4.3 处理后数据规模

| split | 论文 | 问题 | 有金证据的问题 | 金证据片段 | 参考答案字符串 | 证据单元 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train_100 | 100 | 420 | 367 | 761 | 753 | 3,123 |
| validation_50 | 50 | 156 | 151 | 395 | 449 | 1,574 |

证据单元类型：

| split | title | abstract | chunk | figure_caption | table |
| --- | ---: | ---: | ---: | ---: | ---: |
| train_100 | 100 | 100 | 2,254 | 314 | 355 |
| validation_50 | 50 | 50 | 1,129 | 139 | 206 |

validation 单元平均 132.63 词，中位数 123 词，最小 3 词，最大 250 词。

注意：`title` 被保留在处理文件中，但正式检索集合只包含 `abstract`、`chunk`、`table`、`figure_caption` 和 `figure_table`。

## 5. BM25 基线

### 5.1 索引单位与分词

对每篇论文单独建立 BM25 索引，不在不同论文之间检索。分词规则为：

```text
[a-zA-Z0-9_]+
```

文本和问题都转为小写。该规则是透明、可复现的英文词法分词，不做词干化、停用词删除、语义编码或查询扩展。

BM25 使用 `rank-bm25==0.2.2` 的 `BM25Okapi` 默认参数。每个问题分别取 top-1、3、5、10、20，保存排名、BM25 分数、unit 元数据和完整文本。

### 5.2 基线作用

- 小 k 提供低成本但低覆盖的参考点；
- 大 k 提供高覆盖但高成本的参考点；
- top-5、top-10、top-20 同时作为 Ollama 下游生成的对照组。

## 6. ControllerV3 方法细节

### 6.1 非互斥问题类型

控制器用可解释关键词和句式规则判断：

- `is_result`：结果、性能、分数、accuracy、F1、BLEU、ROUGE、baseline、compare 等；
- `is_data`：dataset、data、corpus，以及 language pair、training data、test/development set 等增强模式；
- `is_method`：how、method、approach、model、train、use、supervision 等；
- `is_figure`：figure、fig、architecture、pipeline、diagram、overview；
- `is_definition`：较短的 “what is/are/was” 问题，且不是结果问题；
- `is_abbreviation`：abbreviate、stand(s) for、what does 等，并同时置为 definition；
- `is_complex`：不少于 12 个 token，或以 how/why 开头。

这些标签非互斥。例如同一问题可能同时是 data、method 和 complex。

validation_50 上激活次数为：result 38、data 38、definition 19、method 79、complex 44、abbreviation 2、figure 5。

### 6.2 动作策略

所有问题先对可检索单元做 BM25 排序，最多保留前 20 个候选，并执行：

1. `ReadTop3`：所有问题先读 top-3。
2. 定义/缩写问题：
   - 扩展查询加入 definition、defined、means、refers、stands for 等词；
   - 优先只在 abstract/introduction/background/overview 相关 section 中排名，最多新增 2 个；
   - 如果未增加任何单元，则在全部证据中做定义查询扩展，最多新增 2 个；
   - 随后停止。
3. 结果或数据问题：
   - 将全局阅读预算扩大到排名前 7；
   - 数据问题额外在 data/dataset/corpus/experimental setup/experiments/setup 相关 section 中排名，最多新增 3 个；
   - 从 table 单元的 BM25 top-3 中最多新增 2 个。
4. 方法或复杂问题：把全局阅读预算扩大到前 7。
5. 其他问题：采用默认 top-5。
6. figure 问题：从 figure caption 排名前 2 中最多新增 2 个。
7. `Stop`：记录停止动作和原因。

新增单元按 `unit_id` 去重，并保存 `selected_by`，因此每条结果都能追踪到是哪一项动作选择了它。

### 6.3 实际动作统计

| 动作 | 触发问题次数 | 实际新增单元数 |
| --- | ---: | ---: |
| ReadTop3 | 156 | 468 |
| ReadMoreForResultOrData | 64 | 256 |
| DataSectionExpansion | 34 | 72 |
| ReadTable | 60 | 113 |
| DefinitionIntroExpansion | 19 | 37 |
| ReadMoreForMethodOrComplex | 51 | 204 |
| ReadDefaultTop5 | 22 | 44 |
| ReadFigureCaption | 3 | 5 |
| Stop | 156 | 0 |

figure 标签有 5 个问题，但只有 3 个真正新增 figure caption；其余可能没有候选，或对应 caption 已被前序动作选入。

### 6.4 消融实验

`ControllerV3_no_section` 保留相同问题分类、top-3、扩读、table/figure 和停止规则，但关闭：

- 定义问题的 introduction/abstract/background/overview 章节感知扩展；
- 数据问题的 data/dataset/corpus/experimental setup 章节感知扩展。

定义问题会走全论文定义查询 fallback；数据问题不再获得 data section 专项候选。该消融用于单独检验 section-aware expansion 的贡献。

## 7. 检索评估指标

### 7.1 证据覆盖分数

先把 gold evidence 和每个 retrieved unit 都按同一个正则分词，并转成 token 集合。对一个金证据片段 `g` 和预测单元 `u`：

```text
overlap(g, u) = |tokens(g) ∩ tokens(u)| / |tokens(g)|
```

这是以金证据为分母的非对称覆盖率，不是 Jaccard。一个金证据片段在所有 retrieved units 中取最大 overlap。

### 7.2 正式阈值与聚合

正式阈值为 0.5。

- Evidence Recall：395 个金证据片段中，best overlap ≥ 0.5 的比例。
- Question Hit Rate：151 个有金证据的问题中，至少一个金证据片段被覆盖的比例。
- Average Best Overlap：所有金证据片段 best overlap 的平均值。

没有 gold evidence 的 5 个验证问题不进入检索召回/命中率分母，但仍进入每种方法 156 条的成本与生成统计。

### 7.3 成本指标

- Avg. Retrieved Units：每题选择的证据单元数。
- Avg. Evidence Words：每题选择单元的 word count 之和。
- Avg. Estimated Tokens：`round(avg_evidence_words × 1.3)`，只是英文科学文本的 token 成本代理。
- Recall per 1k Tokens：`evidence_recall / avg_estimated_tokens × 1000`。正式 CSV 先把 recall 四舍五入到 4 位，再计算该值。

这个 token 值不是 Ollama tokenizer 实际输出；实际 prompt token 在生成 API 响应的 `prompt_eval_count` 中另行记录。

## 8. 检索正式结果

| 方法 | Evidence Recall | Hit Rate | Avg. Best Overlap | Avg. Units | Avg. Words | Est. Tokens | Recall/1k |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25_top1 | 0.2304 | 0.3444 | 0.3951 | 1.00 | 166.44 | 216 | 1.0667 |
| BM25_top3 | 0.4253 | 0.5894 | 0.5462 | 3.00 | 521.72 | 678 | 0.6273 |
| BM25_top5 | 0.5646 | 0.7748 | 0.6275 | 5.00 | 889.41 | 1,156 | 0.4884 |
| BM25_top10 | 0.7772 | 0.9007 | 0.7657 | 10.00 | 1,785.85 | 2,322 | 0.3347 |
| BM25_top20 | 0.9519 | 0.9801 | 0.9066 | 19.53 | 3,187.40 | 4,144 | 0.2297 |
| ControllerV3 | 0.7063 | 0.8675 | 0.7231 | 7.69 | 1,261.78 | 1,640 | 0.4307 |
| ControllerV3_no_section | 0.6759 | 0.8344 | 0.6993 | 7.24 | 1,186.74 | 1,543 | 0.4380 |

关键量化结论：

- BM25 top-1 到 top-20 的召回从 0.2304 升至 0.9519，但估算 token 从 216 升至 4,144，证明固定扩大 k 存在明显成本。
- ControllerV3 的召回 0.7063，位于 top-5 的 0.5646 与 top-10 的 0.7772 之间；成本 1,640 token，也位于二者之间。
- 相对 top-10，ControllerV3 少约 29.4% 估算 token，召回低 7.09 个百分点，问题命中率低 3.32 个百分点。
- 相对 top-20，ControllerV3 少约 60.4% 估算 token，但召回低 24.56 个百分点。因此不能声称它在纯召回上胜过大 k，只能声称提供了成本—覆盖折中。
- 相对消融版本，完整 ControllerV3 多约 97 token/题，Evidence Recall 提升 3.04 个百分点，Hit Rate 提升 3.31 个百分点，Average Best Overlap 提升 2.38 个百分点。
- 消融版本的 Recall/1k 略高于完整版本（0.4380 vs 0.4307），说明章节扩展用额外成本换取更高覆盖；这是预期的质量—成本权衡，不应隐藏。
- BM25 top-1 的 Recall/1k 最高，但绝对召回过低。因此 Recall/1k 不能单独作为优劣标准，必须与绝对召回和命中率一起报告。

## 9. 错误分析

错误分析将 ControllerV3 与 BM25 top-20 在阈值 0.5 下比较，只分析 151 个有金证据的问题。

| 类别 | 数量 | 占全部 151 题 | 占 20 个失败题 |
| --- | ---: | ---: | ---: |
| success | 131 | 86.75% | — |
| controller_selection_failure | 10 | 6.62% | 50% |
| retrieval_or_gold_mapping_failure | 3 | 1.99% | 15% |
| figure_selection_failure | 2 | 1.32% | 10% |
| data_evidence_selection_failure | 2 | 1.32% | 10% |
| definition_selection_failure | 1 | 0.66% | 5% |
| result_evidence_selection_failure | 1 | 0.66% | 5% |
| missing_figure_failure | 1 | 0.66% | 5% |

分类是启发式诊断标签：

- 如果 Controller 命中，标为 success；
- 如果 BM25 top-20 也未命中，标为 retrieval_or_gold_mapping_failure；
- 否则再根据动作序列、选择单元类型和问题关键词判断控制器预算、数据、结果、定义或图示选择失败。

逐问题的 gold preview、Controller 最佳单元、BM25 top-20 最佳单元、section、unit type 和 overlap 均保存在 `outputs/error_analysis_controller_v3_validation50.csv`，可以直接选取典型案例写论文。

## 10. 下游生成实验

### 10.1 正式比较方法

下游只比较：

- BM25_top5；
- BM25_top10；
- BM25_top20；
- ControllerV3。

top-1、top-3 和消融版本没有运行生成实验。每种方法 156 个问题，共 624 个 prompt。

### 10.2 提示词与证据截断

提示词要求模型：

- 只使用给定证据；
- 抽取最短正确答案；
- 优先复制证据中的方法、数据集、模型、指标或发现；
- 证据部分相关时给出有支持的部分答案；
- 只有证据明显无关才回答 “Not enough evidence.”；
- 最终只输出答案，不附解释、引用或 evidence 编号。

证据单元按检索顺序加入，每个 block 包含 unit type、section 和 text。加入下一个完整 block 会使证据部分超过 6000 字符时停止；不会截断单个 block。提示词固定说明和问题文本不计入这 6000 字符，因此完整 prompt 最大约 6909 字符。

### 10.3 Ollama 参数

正式运行模型：`qwen2.5:3b`。

| 参数 | 值 |
| --- | --- |
| API | `http://127.0.0.1:11434/api/generate` |
| stream | false |
| keep_alive | 10m |
| num_ctx | 4096 |
| num_predict | 128 |
| temperature | 0.0 |
| seed | 42 |
| retries | 3 |
| 正式运行 timeout | 240 秒/请求 |

脚本当前默认 timeout 为 600 秒；正式全量续跑命令显式使用了 240 秒。timeout 只影响失败等待与重试，不改变模型采样参数。

### 10.4 断点续跑机制

输出采用逐行追加的 JSONL。每次开始时读取已有 `status=ok` 的 `(method, question_id)`，只处理未完成记录。每个请求最多重试 3 次，成功/失败都立即写一行。因此锁屏、关机或终端中断后可重复执行相同方法命令。

正式记录的运行顺序为 BM25_top5、BM25_top10、BM25_top20、ControllerV3。BM25_top5 跨多次中断/恢复完成，其 `avg_wall_time_seconds=6047.644` 明显受到暂停或系统休眠影响，不能作为性能数据。其他 wall-time 也未在严格相同的热启动条件下控制，论文不应报告方法间速度比较。

## 11. 答案评估指标

### 11.1 答案归一化

预测与参考答案均：

1. 转小写并去两侧空白；
2. 把 “Not enough evidence.”、“Insufficient evidence” 和 “unanswerable” 统一为 `unanswerable`；
3. 去英文标点；
4. 删除独立冠词 `a`、`an`、`the`；
5. 压缩空白。

### 11.2 Token F1 与 Exact Match

Token F1 用 `Counter` 计算预测与参考 token 的多重集交集，再计算 precision、recall 和调和平均。一个问题可能有多个参考答案，F1 和 EM 都取所有参考中的最大值。

EM 要求归一化后的预测与至少一个参考完全相同。正式汇总只对 `status=ok` 记录取平均；本次所有 624 条都成功。

## 12. 生成正式结果

| 方法 | Answer F1 | Exact Match | 成功 | Avg Prompt Tokens | Avg Output Tokens |
| --- | ---: | ---: | ---: | ---: | ---: |
| BM25_top5 | 0.259133 | 0.121795 | 156/156 | 1,243.39 | 8.95 |
| BM25_top10 | 0.262938 | 0.128205 | 156/156 | 1,309.10 | 10.19 |
| BM25_top20 | 0.257749 | 0.121795 | 156/156 | 1,309.10 | 9.93 |
| ControllerV3 | 0.257732 | 0.121795 | 156/156 | 1,295.44 | 9.96 |

分布细节：

| 方法 | F1 中位数 | F1=0 | F1>0 | F1≥0.5 | EM 题数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| BM25_top5 | 0.000000 | 79 | 77 | 36 | 19 |
| BM25_top10 | 0.063054 | 76 | 80 | 36 | 20 |
| BM25_top20 | 0.044196 | 77 | 79 | 35 | 19 |
| ControllerV3 | 0.044196 | 77 | 79 | 35 | 19 |

ControllerV3 与各基线的逐问题 F1：

| 比较 | Controller 胜 | 平 | 负 | 平均 F1 差（Controller−Baseline） |
| --- | ---: | ---: | ---: | ---: |
| vs BM25_top5 | 14 | 130 | 12 | -0.001402 |
| vs BM25_top10 | 6 | 143 | 7 | -0.005206 |
| vs BM25_top20 | 4 | 148 | 4 | -0.000017 |

合理结论是：ControllerV3 在较低检索成本下，下游答案质量与固定 top-k 大体相当；不能宣称它显著提高了回答质量。

## 13. 生成实验中必须披露的提示词上限效应

重新审计 624 个 prompt 后发现：

| Prompt 对 | 完全相同 | 不同 | 总数 |
| --- | ---: | ---: | ---: |
| BM25_top10 vs BM25_top20 | 156 | 0 | 156 |
| BM25_top5 vs BM25_top10 | 121 | 35 | 156 |
| ControllerV3 vs BM25_top5 | 114 | 42 | 156 |
| ControllerV3 vs BM25_top10 | 134 | 22 | 156 |
| ControllerV3 vs BM25_top20 | 134 | 22 | 156 |

这说明 6000 字符上限使很多方法在进入模型前变成相同 prompt。特别是 BM25 top-10 与 top-20 的 156 对输入全部相同，所以两者 F1 的微小差异不可能由 top-20 额外证据造成。

尽管 temperature=0、seed=42，BM25 top-10 与 top-20 的相同 prompt 仍有 9/156 对生成答案文本不同，147/156 完全相同。这表明在跨时段、断点恢复的本地推理中，当前配置没有产生逐字符完全确定的结果；top-10 与 top-20 的答案差异应视为运行非完全确定性，而不是检索方法效应。

论文中应明确区分：

- 检索实验的成本：对完整 retrieved units 统计，top-20 的成本确实高于 top-10；
- 生成实验的模型输入：受 6000 字符上限约束，top-10 与 top-20 实际输入相同。

因此，生成实验是“固定上下文窗口下的下游可用性验证”，不是“让模型读取完整 top-k 后的端到端成本实验”。

## 14. 现有实验能支持的论文主张

可以支持：

- 大 top-k 提高证据覆盖，同时显著增加证据阅读成本；
- 一个规则化、问题感知、可追踪动作的控制器能够在 top-5 与 top-10 之间提供可解释预算点；
- section-aware expansion 在小规模验证子集上提高了证据召回和问题命中率；
- ControllerV3 的较低成本证据在固定字符上限的本地 3B 模型中取得了与固定 top-k 相近的答案 F1/EM；
- 控制器失败主要集中在一般选择失败，以及少量图、数据、定义、结果证据选择失败。

不能支持：

- ControllerV3 的绝对召回优于 BM25 top-10/top-20；
- ControllerV3 的 Recall/1k 是所有方法最高；
- ControllerV3 显著提高答案 F1/EM；
- top-20 的额外证据改善或损害了生成，因为其 prompt 与 top-10 全部相同；
- wall-clock 更快，因为运行过程有中断、缓存和热启动差异；
- 结果已经证明可泛化到 QASPER 全量或其他科学问答数据集。

## 15. 方法学局限与论文风险

### 15.1 数据规模与划分

正式结果只使用 validation 前 50 篇、156 个问题。它能支撑毕业设计的原型验证与消融分析，但样本量和代表性有限。

### 15.2 开发集与评估集未严格分离

ControllerV3 注释明确说明部分增强规则来自错误分析，而最终又在同一 validation_50 上报告指标。因此结果可能包含对该子集的人工调优，不能视为完全独立 held-out test 的泛化结论。论文应把它称为 validation study 或原型评估；如果时间允许，最有价值的补充是冻结规则后在新的 held-out 子集重新运行。

### 15.3 成本是代理指标

检索 token 成本由英文词数乘 1.3 估算，不是具体模型 tokenizer 的账单 token。生成结果另有实际 `prompt_eval_count`，二者用途不同。

### 15.4 检索匹配指标是词法代理

gold evidence 与 retrieved unit 可能粒度不同；token-set overlap 不关心词序和重复，也不能识别语义等价表达。`retrieval_or_gold_mapping_failure` 可能同时包含 BM25 失败和证据分块/标注映射问题。

### 15.5 基线范围有限

正式基线是透明的 BM25 fixed top-k，没有 dense retriever、cross-encoder reranker、学习型策略或强 API 模型。这适合强调低资源和可解释性，但论文不能声称击败当前最先进方法。

### 15.6 缺少统计显著性和人工评估

当前报告宏平均 F1/EM 和逐问题胜平负，没有 bootstrap 置信区间、显著性检验或人工正确性/忠实性评分。结果差异很小，尤其不能把小数点后三位的差异解释成稳定优势。

## 16. 正式文件与证据链

- 原始处理数据：`data/processed/*.jsonl`；
- 逐问题检索结果：`outputs/validation50_*.jsonl`；
- 检索汇总：`outputs/validation50_method_comparison_threshold05.csv`；
- 错误分析：`outputs/error_analysis_controller_v3_validation50.csv`；
- 生成 prompt：`outputs/generation_prompts_validation50.jsonl`；
- Ollama 原始响应：`outputs/ollama_generations_validation50.jsonl`；
- 逐回答得分：`outputs/ollama_answer_scores_validation50.csv`；
- 回答汇总：`outputs/ollama_answer_summary_validation50.csv`；
- 独立重算审计：`docs/experiment_audit.json`；
- 结果总表：`docs/experiment_results_overview.csv`；
- 文件哈希：`docs/file_manifest_sha256.csv`。

论文表格优先引用原始 `outputs` CSV；需要更多分布、动作、paired comparison 和完整性信息时引用 `experiment_audit.json`。不要把 README 中的四舍五入表当作唯一数据来源。

## 17. 总结

这项工作已经形成从 QASPER 预处理、可解释检索控制、固定预算基线、成本指标、消融、错误分析、本地生成到答案评分的完整闭环。其最稳健的贡献不是“取得最高答案分数”，而是：在资源受限条件下构建了一个透明、可追踪、可以量化质量—成本权衡的科学问答证据控制框架，并用章节扩展消融和本地生成验证了其行为。

完整复现命令见 `REPRODUCTION_GUIDE_ZH.md`，逐字段解释见 `DATA_DICTIONARY_ZH.md`，论文写作素材见 `THESIS_WRITING_MATERIAL_ZH.md`。
