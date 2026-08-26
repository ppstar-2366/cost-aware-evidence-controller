# 数据字典与文件说明

## 1. 目录结构

```text
cost_aware_evidence_controller/
├─ README.md
├─ requirements.txt
├─ src/
│  ├─ common.py
│  ├─ retrieval.py
│  ├─ build_evidence_units.py
│  ├─ check_processed_data.py
│  ├─ run_controller_v3.py
│  ├─ run_retrieval_experiment.py
│  ├─ build_generation_prompts.py
│  ├─ run_ollama_generation.py
│  ├─ evaluate_generated_answers.py
│  └─ audit_experiments.py
├─ data/processed/
│  ├─ qasper_train_100.jsonl
│  └─ qasper_validation_50.jsonl
├─ outputs/
│  ├─ validation50_bm25_top*.jsonl
│  ├─ validation50_controller_v3.jsonl
│  ├─ validation50_controller_v3_no_section.jsonl
│  ├─ validation50_method_comparison_threshold05.csv
│  ├─ error_analysis_controller_v3_validation50.csv
│  ├─ generation_prompts_validation50.jsonl
│  ├─ ollama_generations_validation50.jsonl
│  ├─ ollama_answer_scores_validation50.csv
│  └─ ollama_answer_summary_validation50.csv
└─ docs/
   ├─ README.md
   ├─ EXPERIMENT_ARCHIVE_ZH.md
   ├─ REPRODUCTION_GUIDE_ZH.md
   ├─ DATA_DICTIONARY_ZH.md
   ├─ THESIS_WRITING_MATERIAL_ZH.md
   ├─ environment_snapshot.txt
   ├─ experiment_audit.json
   ├─ experiment_results_overview.csv
   └─ file_manifest_sha256.csv
```

JSONL 表示一行一个 JSON 对象。CSV 均为 UTF-8；`docs` 下新生成的 CSV 使用 UTF-8 with BOM，便于 Windows Excel 正确显示中文。

## 2. 源码职责

### `src/common.py`

公共函数：

- `read_jsonl` / `write_jsonl`；
- `read_csv` / `write_csv`；
- `tokenize`：小写后用 `[a-zA-Z0-9_]+` 分词；
- `estimate_tokens_from_words`：英文词数 × 1.3；
- `extract_reference_answers`：从 QASPER raw answer 提取 unanswerable、free form、extractive spans、yes/no；
- `extract_gold_evidence`：提取、规范化并去重 gold evidence；
- `mean`。

### `src/retrieval.py`

检索与评估核心：

- 正式可检索类型：`abstract`、`chunk`、`table`、`figure_caption`、`figure_table`；
- 每篇论文单独建立 BM25；
- 运行 fixed top-k；
- 计算 token-set overlap、Evidence Recall、Question Hit Rate、Average Best Overlap；
- 统计证据单元、词数、估算 token、动作和 unit type；
- 基础问题类型识别；
- 控制器候选去重加入。

### `src/build_evidence_units.py`

从 Hugging Face QASPER 构建处理数据。默认 train 100、validation 50。正文块最大 250 词、重叠 40 词。

### `src/check_processed_data.py`

只读检查脚本，输出论文、问题、unit type 数量和首篇样例。

### `src/run_controller_v3.py`

完整问题类型增强、section-aware expansion、动作策略和消融开关。可作为模块被统一实验脚本调用。

该文件的独立入口已改为当前 `qasper_validation_50.jsonl`，可用于单独运行 Controller 并生成 0.3/0.5/0.7 阈值扫描；正式论文主实验入口仍是 `src/run_retrieval_experiment.py`。

### `src/run_retrieval_experiment.py`

正式检索入口。运行 BM25 1/3/5/10/20、ControllerV3、无 section 消融、汇总和错误分析。默认阈值 0.5。

### `src/build_generation_prompts.py`

把 top-5、top-10、top-20、ControllerV3 的检索结果转换为 624 个 prompt。证据字符上限 6000。

### `src/run_ollama_generation.py`

调用 Ollama `/api/generate`，保存原始响应元数据；支持按方法筛选、全局 limit、per-method limit、重试和断点续跑。

### `src/evaluate_generated_answers.py`

按 `(method, question_id)` 取最后一条记录，计算归一化 Token F1 和 EM，输出逐题与方法汇总 CSV。

### `src/audit_experiments.py`

只读取正式数据和输出，独立重算描述统计、prompt 相同性、回答分布和 paired comparison；生成机器审计 JSON、Excel 兼容结果总表和 SHA-256 清单。

## 3. 处理数据 JSONL

文件：

- `data/processed/qasper_train_100.jsonl`：100 行；
- `data/processed/qasper_validation_50.jsonl`：50 行。

每行是一篇论文：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `paper_id` | string | QASPER 论文唯一 ID |
| `title` | string | 规范化论文标题 |
| `evidence_units` | list[object] | 该论文所有结构化证据单元 |
| `questions` | list[object] | 该论文的问题与原始答案 |
| `num_units` | integer | `evidence_units` 数量 |
| `num_questions` | integer | `questions` 数量 |

### `evidence_units[]`

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `paper_id` | string | 所属论文 ID |
| `unit_id` | string | 单元唯一 ID，格式近似 `{paper}_{type}_{index}` |
| `unit_type` | string | `title` / `abstract` / `chunk` / `table` / `figure_caption` / 可能的 `figure_table` |
| `section_name` | string | 原论文 section 名；图表统一为 `Figures and Tables` |
| `text` | string | 规范化证据文本 |
| `position` | integer | 在该论文证据序列中的位置 |
| `source_id` | string | 正文块的 section/chunk ID 或图表文件名 |
| `word_count` | integer | 以空格切分的词数 |

### `questions[]`

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `paper_id` | string | 所属论文 ID |
| `question_id` | string | QASPER 问题唯一 ID |
| `question` | string | 规范化问题文本 |
| `raw_answers` | object | QASPER 原始答案结构，供后续提取参考答案和 gold evidence |

## 4. BM25 检索 JSONL

文件：`outputs/validation50_bm25_top1.jsonl`、top3、top5、top10、top20。

每个文件 156 行，每行对应一个问题：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `paper_id` | string | 论文 ID |
| `title` | string | 论文标题 |
| `question_id` | string | 问题 ID |
| `question` | string | 问题文本 |
| `reference_answers` | list[string] | 从 raw answer 提取的全部可评估参考答案 |
| `gold_evidence` | list[string] | 去重后的 gold evidence 文本 |
| `retrieved_units` | list[object] | 该 top-k 选择的证据单元 |

### BM25 `retrieved_units[]`

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `rank` | integer | 在该问题中的 BM25 排名，从 1 开始 |
| `score` | float | `BM25Okapi` 分数 |
| `unit_id` | string | 证据单元 ID |
| `unit_type` | string | 单元类型 |
| `section_name` | string | section 名 |
| `text` | string | 完整单元文本 |
| `word_count` | integer | 单元词数 |

top-20 的平均单元数是 19.53 而不是 20，因为少数论文可检索单元不足 20。

## 5. Controller JSONL

文件：

- `outputs/validation50_controller_v3.jsonl`；
- `outputs/validation50_controller_v3_no_section.jsonl`。

每个文件 156 行，包含 BM25 文件的公共字段，并新增：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `question_type` | object[string,bool] | 非互斥问题标签 |
| `actions` | list[object] | 控制器实际动作序列 |

Controller 的 `retrieved_units[]` 还包含：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `selected_by` | string | 首次选择该单元的动作名称 |

### `actions[]`

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `action` | string | 动作名，例如 `ReadTop3`、`DataSectionExpansion`、`Stop` |
| `added_units` | integer | 该动作新增的去重单元数 |
| `reason` | string | 可解释的动作原因 |

## 6. 检索汇总 CSV

文件：`outputs/validation50_method_comparison_threshold05.csv`，7 行。

| 字段 | 含义 |
| --- | --- |
| `method` | 方法名 |
| `threshold` | gold evidence 命中的 overlap 阈值，正式值 0.5 |
| `total_questions_with_gold` | 有 gold evidence 的问题数，151 |
| `question_hit_rate` | 至少覆盖一条 gold evidence 的问题比例 |
| `evidence_recall` | 被覆盖 gold evidence span 比例 |
| `average_best_overlap` | 每条 gold 对检索单元的最大 overlap 平均值 |
| `avg_retrieved_units` | 平均检索单元数 |
| `avg_evidence_words` | 平均证据词数 |
| `avg_estimated_tokens` | `round(avg words × 1.3)` |
| `avg_chunks` | 每题平均 chunk 数 |
| `avg_tables` | 每题平均 table 数 |
| `avg_figures` | 每题平均 figure_caption 数 |
| `avg_abstracts` | 每题平均 abstract 数 |
| `avg_action_steps` | 每题平均控制器动作数；BM25 为 0 |
| `recall_per_1k_tokens` | 每 1000 个估算 token 的 recall |

## 7. 错误分析 CSV

文件：`outputs/error_analysis_controller_v3_validation50.csv`，151 行。

| 字段 | 含义 |
| --- | --- |
| `paper_id` / `question_id` / `question` | 样本身份与问题 |
| `category` | 启发式错误类别或 `success` |
| `controller_hit` | Controller best overlap 是否 ≥ 0.5 |
| `controller_best_overlap` | Controller 在全部 gold/unit 对中的最高 overlap |
| `bm25_top20_hit` | BM25 top-20 是否命中 |
| `bm25_top20_best_overlap` | BM25 top-20 最高 overlap |
| `action_sequence` | Controller 动作链 |
| `selected_types` | 所选 unit type 与数量，例如 `chunk:7; table:2` |
| `gold_evidence_preview` | 最佳对应 gold 的前 350 字符 |
| `controller_best_unit_type` | Controller 最佳单元类型 |
| `controller_best_section` | Controller 最佳单元 section |
| `controller_best_text_preview` | Controller 最佳单元前 350 字符 |
| `bm25_best_unit_type` | BM25 top-20 最佳单元类型 |
| `bm25_best_section` | BM25 top-20 最佳单元 section |
| `bm25_best_text_preview` | BM25 top-20 最佳单元前 350 字符 |

注意：一行只保存全体 gold 中的“总体最佳”匹配，不是每条 gold 各一行。

## 8. 生成 prompt JSONL

文件：`outputs/generation_prompts_validation50.jsonl`，624 行。

| 字段 | 含义 |
| --- | --- |
| `method` | BM25_top5 / top10 / top20 / ControllerV3 |
| `paper_id` | 论文 ID |
| `question_id` | 问题 ID |
| `question` | 问题文本 |
| `reference_answers` | 全部参考答案字符串 |
| `gold_evidence` | gold evidence 列表 |
| `num_retrieved_units` | 字符截断前检索输出中的单元数 |
| `prompt` | 实际提交给 Ollama 的完整 prompt |

`num_retrieved_units` 不等于最终真正进入 prompt 的单元数，因为 prompt builder 只保存完整 prompt，没有单独保存截断后的 unit count。字符预算为 6000。

## 9. Ollama 原始生成 JSONL

文件：`outputs/ollama_generations_validation50.jsonl`，624 行。

| 字段 | 含义 |
| --- | --- |
| `method` / `paper_id` / `question_id` / `question` | 样本身份 |
| `reference_answers` / `gold_evidence` | 评估与追踪信息 |
| `num_retrieved_units` | prompt 源记录中的检索单元数 |
| `model` | Ollama 返回的模型名，本次均为 `qwen2.5:3b` |
| `status` | `ok` 或 `error`，本次均为 `ok` |
| `generated_answer` | 模型答案文本 |
| `done_reason` | Ollama 停止原因，本次均为 `stop` |
| `prompt_eval_count` | Ollama 实际处理的 prompt token 数 |
| `eval_count` | 生成 token 数 |
| `total_duration_ns` | Ollama 总耗时，纳秒 |
| `load_duration_ns` | 模型加载耗时，纳秒 |
| `prompt_eval_duration_ns` | prompt 处理耗时，纳秒 |
| `eval_duration_ns` | 生成耗时，纳秒 |
| `wall_time_seconds` | Python 请求外部计时；受中断/休眠污染 |
| `error` | 最后一次错误文本；成功记录为空 |
| `created_at` | UTC ISO 时间 |

## 10. 回答逐题评分 CSV

文件：`outputs/ollama_answer_scores_validation50.csv`，624 行。

| 字段 | 含义 |
| --- | --- |
| `method` / `paper_id` / `question_id` / `question` | 样本身份 |
| `status` | 生成状态 |
| `generated_answer` | 原始生成答案 |
| `reference_answers` | JSON 字符串形式的参考答案列表 |
| `answer_f1` | 与最佳参考答案的 token F1 |
| `exact_match` | 与任一参考归一化后完全匹配，0 或 1 |
| `prompt_tokens` | Ollama `prompt_eval_count` |
| `output_tokens` | Ollama `eval_count` |
| `wall_time_seconds` | 诊断计时，不用于方法速度结论 |
| `model` | 模型名 |
| `error` | 错误文本 |

## 11. 回答汇总 CSV

文件：`outputs/ollama_answer_summary_validation50.csv`，4 行。

| 字段 | 含义 |
| --- | --- |
| `method` / `model` | 方法与模型 |
| `total_records` | 最新唯一记录数 |
| `successful_records` | 成功记录数 |
| `success_rate` | 成功率 |
| `answer_f1` | 成功记录的宏平均 F1 |
| `exact_match` | 成功记录的宏平均 EM |
| `avg_prompt_tokens` | 平均实际 prompt token |
| `avg_output_tokens` | 平均输出 token |
| `total_prompt_tokens` | 全部 prompt token 总和 |
| `total_output_tokens` | 全部输出 token 总和 |
| `avg_wall_time_seconds` | 诊断平均耗时；本实验不可做方法比较 |

## 12. docs 机器档案

### `experiment_audit.json`

包含：

- 数据规模和 unit type；
- 每个检索文件从原始 JSONL 重算的指标；
- Controller 标签、动作、动作序列、selected-by 分布；
- 错误类别数量与比例；
- prompt 长度和成对相同性；
- 生成状态、token、时间区间；
- F1 分布、逐问题胜平负；
- 成对生成答案相同性；
- 关键 artifact 的字段、记录数、大小和哈希。

### `experiment_results_overview.csv`

7 行统一方法总表，把检索指标与可用的生成指标放在同一行。top-1/top-3/消融没有生成实验，因此生成列为空。可直接用 Excel 打开、筛选和复制到论文。

### `file_manifest_sha256.csv`

| 字段 | 含义 |
| --- | --- |
| `relative_path` | 相对项目根目录的路径 |
| `size_bytes` | 文件字节数 |
| `sha256` | 文件内容 SHA-256 |
| `modified_at_local` | 本地修改时间 |

清单排除自身，避免每次生成后自引用哈希变化；包括审计 JSON、源码、数据、输出和其他 docs。

## 13. 正式引用优先级

写论文时按以下顺序取数：

1. `outputs/validation50_method_comparison_threshold05.csv`：正式检索主表；
2. `outputs/ollama_answer_summary_validation50.csv`：正式生成主表；
3. `outputs/error_analysis_controller_v3_validation50.csv`：典型案例；
4. `outputs/ollama_answer_scores_validation50.csv`：逐问题生成细节；
5. `docs/experiment_audit.json`：分布、动作、paired comparison 和完整性验证；
6. README/Markdown 表格：便于阅读，但不是唯一原始数据源。

## 14. 2026-08-27 test 与补充实验扩展

第 1–13 节保留的是 Validation50 开发归档。终期论文引用优先级已由完整官方
test416 和冻结的 paper-cluster generation sample 取代，Validation50 不再称为
正式独立终评。

### 检索与 bootstrap

- `outputs/test416/test416_method_comparison_threshold05.csv`：完整 test 主检索表；
- `outputs/test416/test416_bootstrap_method_cis.csv`：方法级 paper bootstrap 区间；
- `outputs/test416/test416_bootstrap_paired_differences.csv`：预先指定的 paired 差值；
- `outputs/supplementary/test416_supplementary_retrieval_summary.csv`：abstract-only、
  read-all 和预算匹配对照；
- `outputs/supplementary/test416_controller_behavior_*.csv`：可变预算、路径和动作诊断。

### 冻结 test 生成

- `test_generation_sample_manifest.json`：53 个完整 paper clusters、201 个问题和
  固定 seed 的样本身份；
- `test_generation_prompt_audit.json`：804 个方法—问题记录、608 个 unique prompt、
  截断与方法对齐审计；
- `test_generation_unique_generations.jsonl`：每个唯一 prompt 一条 Ollama 返回；大文件
  留在本地且被 Git 忽略；
- `test_generation_answer_details.csv`：把唯一生成结果映射回每个方法—问题，并保存
  Answer F1、EM、答案类型、实际输入/输出 token；
- `test_generation_answer_summary.csv` 与 `test_generation_answer_by_type.csv`：方法级
  和答案类型级汇总；
- `test_generation_answer_bootstrap_method_cis.csv`：方法级 F1、EM、prompt/output token
  的 95% paper-cluster bootstrap 区间；
- `test_generation_answer_bootstrap_paired.csv`：ControllerV3 相对 top-7、top-8、
  no-section 的 paired 差值与区间；
- `test_generation_integrity_audit.json`：对齐、缺失、API 失败、长度截断、上下文、
  prompt 去重实际成本和理论未去重成本；
- `test_generation_sha256_manifest.csv`：协议、脚本和本地大文件的 SHA-256 证据链。

### 图表

`outputs/figures/` 中的 PDF 是 LaTeX 首选矢量文件，PNG 是 400 dpi RGB 复核版本。
`figure_manifest.json` 保存数据源与输出哈希、变换说明和 alt text。图表的推荐 caption
及结论边界见 `docs/THESIS_FIGURE_GUIDE.md`。

终期论文应首先引用 test416 的主检索结果和冻结 test generation sample；第 13 节
列出的 Validation50 文件只用于开发史、补充诊断或与旧草稿核对。
