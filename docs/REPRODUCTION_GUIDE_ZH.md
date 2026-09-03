# 实验复现说明

本文档给出两种复现路径：

- **只查看和验证已有结果**：不需要重新下载 QASPER，也不需要重新运行 Ollama；
- **从头重跑完整实验**：需要 Python、网络、Ollama 和较长运行时间。

第1--8节保留早期 Windows Validation50 开发环境的执行记录；第9节给出冻结测试与补充实验的 macOS/VS Code 命令。所有相对路径均以仓库根目录为起点。

## 1. 换机时应复制什么

复制整个项目文件夹，至少必须包括：

```text
README.md
requirements.txt
src/
data/processed/
outputs/
docs/
```

`.venv/` 不建议跨机器复制；在新机器重建。Ollama 模型目录体积较大，可以重新 `pull`，也可以按 Ollama 官方兼容方式迁移，但不要把 `data/processed` 或 `outputs` 当作可随时重建的缓存而删除。

## 2. 最快验证已有成果

已有 `outputs/` 完整时，只需 Python 环境即可验证，不需要启动 Ollama。

### 2.1 创建虚拟环境

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

如果新机器没有 Python 3.13，可以使用兼容的 Python 3.10+；但为了最大程度复现最终环境，建议 3.13.5。

### 2.2 运行审计

```powershell
.\.venv\Scripts\python.exe src\audit_experiments.py
```

正确输出应包含：

```text
Generation records: 624 unique latest records
BM25_top5: 156/156 successful
BM25_top10: 156/156 successful
BM25_top20: 156/156 successful
ControllerV3: 156/156 successful
```

脚本会刷新：

- `docs/experiment_audit.json`；
- `docs/experiment_results_overview.csv`；
- `docs/file_manifest_sha256.csv`。

它不会修改 `data/processed` 或 `outputs`。

### 2.3 快速查看正式结果

```powershell
Get-Content outputs\validation50_method_comparison_threshold05.csv
Get-Content outputs\ollama_answer_summary_validation50.csv
```

## 3. 最终实验环境快照

完成正式实验时的核心环境：

```text
OS kernel: Microsoft Windows NT 10.0.26200.0, x64
CPU: Intel Core i5-10210U @ 1.60 GHz
Logical processors visible: 8
RAM: 7.8 GB
GPU: Intel UHD Graphics
Python: 3.13.5
Ollama: 0.30.10
Model: qwen2.5:3b, ID 357c53fb659c, about 1.9 GB
```

`requirements.txt` 记录运行所需的 Python 依赖。需要逐次复现实验时，还应保存所用 Python、Ollama 和模型版本，因为最低版本约束不保证跨环境逐字节一致。

## 4. Ollama 在 D 盘的配置

最终机器的路径：

```text
D:\Ollama\ollama.exe
D:\OllamaModels
```

用户级模型目录环境变量：

```powershell
[Environment]::SetEnvironmentVariable(
    'OLLAMA_MODELS',
    'D:\OllamaModels',
    'User'
)
$env:OLLAMA_MODELS = 'D:\OllamaModels'
```

确认版本和模型：

```powershell
& 'D:\Ollama\ollama.exe' --version
& 'D:\Ollama\ollama.exe' list
```

新机器没有模型时：

```powershell
& 'D:\Ollama\ollama.exe' pull qwen2.5:3b
```

确认本地服务：

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

如果访问失败，先启动 Ollama。根据安装方式，可以启动桌面程序，或在隐藏窗口中运行服务：

```powershell
Start-Process `
    -FilePath 'D:\Ollama\ollama.exe' `
    -ArgumentList 'serve' `
    -WindowStyle Hidden
```

## 5. 从头重跑完整实验

以下步骤会覆盖同名的检索、prompt 和评分文件。重新生成 Ollama 输出前应先备份正式 `outputs/ollama_generations_validation50.jsonl`；生成脚本本身采用追加和断点续跑，不会自动清空旧文件。

### 5.1 重建处理数据（通常不需要）

该步骤需要联网访问 Hugging Face：

```powershell
.\.venv\Scripts\python.exe src\build_evidence_units.py `
    --train-papers 100 `
    --validation-papers 50 `
    --train-output data\processed\qasper_train_100.jsonl `
    --validation-output data\processed\qasper_validation_50.jsonl
```

预期规模：

- train：100 篇、420 问题、3,123 个证据单元；
- validation：50 篇、156 问题、1,574 个证据单元。

如果 Hugging Face 数据版本变化，应保留当前处理文件和 SHA-256，论文以当前保存版本为准。

检查数据：

```powershell
.\.venv\Scripts\python.exe src\check_processed_data.py `
    --input data\processed\qasper_validation_50.jsonl
```

### 5.2 重跑检索、消融与错误分析

正式命令：

```powershell
.\.venv\Scripts\python.exe src\run_retrieval_experiment.py `
    --input data\processed\qasper_validation_50.jsonl `
    --output-dir outputs `
    --threshold 0.5 `
    --top-k 1 3 5 10 20
```

不加 `--skip-ablation`，因此会运行 `ControllerV3_no_section`。不加 `--skip-error-analysis`，并且 top-k 中包含 20，因此会生成错误分析。

预期正式输出：

```text
outputs/validation50_bm25_top1.jsonl
outputs/validation50_bm25_top3.jsonl
outputs/validation50_bm25_top5.jsonl
outputs/validation50_bm25_top10.jsonl
outputs/validation50_bm25_top20.jsonl
outputs/validation50_controller_v3.jsonl
outputs/validation50_controller_v3_no_section.jsonl
outputs/validation50_method_comparison_threshold05.csv
outputs/error_analysis_controller_v3_validation50.csv
```

提示：汇总文件名固定包含 `threshold05`。如果将命令的 `--threshold` 改为其他值，当前代码仍使用这个文件名，因此实验报告必须同时记录真实命令参数，避免只从文件名推断阈值。

### 5.3 生成 Ollama prompts

```powershell
.\.venv\Scripts\python.exe src\build_generation_prompts.py `
    --output outputs\generation_prompts_validation50.jsonl
```

默认输入为：

- BM25_top5；
- BM25_top10；
- BM25_top20；
- ControllerV3。

预期共 624 条 prompt，每种方法 156 条。证据部分字符预算为 6000。

### 5.4 全量运行本地回答生成

为了易于观察和断点恢复，正式全量运行按方法分别执行：

```powershell
.\.venv\Scripts\python.exe src\run_ollama_generation.py `
    --model qwen2.5:3b `
    --methods BM25_top5 `
    --output outputs\ollama_generations_validation50.jsonl `
    --timeout 240 `
    --num-predict 128
```

```powershell
.\.venv\Scripts\python.exe src\run_ollama_generation.py `
    --model qwen2.5:3b `
    --methods BM25_top10 `
    --output outputs\ollama_generations_validation50.jsonl `
    --timeout 240 `
    --num-predict 128
```

```powershell
.\.venv\Scripts\python.exe src\run_ollama_generation.py `
    --model qwen2.5:3b `
    --methods BM25_top20 `
    --output outputs\ollama_generations_validation50.jsonl `
    --timeout 240 `
    --num-predict 128
```

```powershell
.\.venv\Scripts\python.exe src\run_ollama_generation.py `
    --model qwen2.5:3b `
    --methods ControllerV3 `
    --output outputs\ollama_generations_validation50.jsonl `
    --timeout 240 `
    --num-predict 128
```

没有显式列出的正式默认参数：

```text
base_url=http://127.0.0.1:11434
retries=3
num_ctx=4096
temperature=0.0
seed=42
stream=false
keep_alive=10m
```

#### 中断后怎么继续

直接重新执行相同方法命令。脚本会跳过已有 `status=ok` 的 `(method, question_id)`。

不要手工把部分输出复制成另一个同名文件后再拼接，也不要同时启动两个进程写同一个 JSONL。一个方法一个前台进程最安全。

#### 查看当前进度

```powershell
.\.venv\Scripts\python.exe -c "import json,collections; p='outputs/ollama_generations_validation50.jsonl'; rows=[json.loads(x) for x in open(p,encoding='utf-8') if x.strip()]; print('records',len(rows)); print(collections.Counter((r.get('method'),r.get('status')) for r in rows))"
```

#### 慢机器设置

当前机器只有 8 GB 内存和集成显卡。若请求超时，可以把 `--timeout` 调为 600；这不改变温度、seed、上下文或输出长度，但会延长失败前等待时间。

避免锁屏后自动休眠或直接关机。即使中断，输出可续跑，但 wall-time 会失去可比性。

### 5.5 评估回答

```powershell
.\.venv\Scripts\python.exe src\evaluate_generated_answers.py `
    --input outputs\ollama_generations_validation50.jsonl `
    --details outputs\ollama_answer_scores_validation50.csv `
    --summary outputs\ollama_answer_summary_validation50.csv
```

预期：4 种方法各 156 条，总计 624 条，全部成功。

### 5.6 最终审计

```powershell
.\.venv\Scripts\python.exe src\audit_experiments.py
```

审计会重新从逐问题原始文件统计数据规模、检索指标、动作分布、错误类别、prompt 相同性、回答分布和 paired comparison，并更新哈希清单。

## 6. 正式结果验收标准

完成一次复现后应逐项确认：

- 两个处理数据文件分别为 100、50 行（每行一篇论文）；
- 每个检索 JSONL 为 156 条，且 question ID 唯一；
- 检索汇总为 7 行方法；
- 错误分析为 151 行；
- prompt JSONL 为 624 条；
- generation JSONL 最新唯一键为 624，4 种方法均 156/156 `ok`；
- answer score CSV 为 624 行；
- answer summary CSV 为 4 行；
- 审计输出没有 missing artifact；
- 新结果的 SHA-256 与旧清单不同是正常的，但必须保存新的清单并说明重跑环境。

## 7. 不建议重跑或覆盖的场景

只是在另一台机器写论文时，不需要重跑本地模型。复制当前 `outputs` 和 `docs` 即可，因为正式生成耗时长，并且相同 prompt 在跨时段 Ollama 推理中也未做到逐字符完全确定。

如果只想重算论文表格，运行 `src/audit_experiments.py` 即可；如果只想重算 F1/EM，运行 `src/evaluate_generated_answers.py` 即可。两者都不需要启动 Ollama。

## 8. 常见问题

### Ollama 无法连接

先运行：

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

确认服务、端口和模型列表。脚本在开始生成前会执行健康检查。

### 模型又占 C 盘

确认用户环境变量和当前 PowerShell 会话变量都是 `D:\OllamaModels`，然后再 pull 模型。

### 生成文件已经有一部分

不要删除。重复执行同一方法，脚本会跳过成功记录。

### 为什么 top-10 和 top-20 的回答差不多

正式 prompt 有 6000 字符证据上限，二者 156 对 prompt 全部相同。微小回答差异来自本地推理未完全确定，而不是 top-20 额外证据。

### 能否用 wall-time 写速度对比

不能。BM25_top5 跨越中断和恢复，平均 wall-time 被严重污染；其余方法也没有统一冷启动、缓存和系统负载条件。

## 9. 当前 macOS / VS Code 冻结 test 流程

第 1–8 节保留早期 Windows Validation50 复现史。当前终期实验已经在 macOS 项目
目录的 `.venv` 中配置好，并在 `.vscode/tasks.json` 提供可从 VS Code 的
“Tasks: Run Task”直接执行的任务。正式生成任务显式固定
`qwen2.5:3b`、`num_ctx=8192`、`num_predict=256`、`temperature=0`、`seed=42`。

命令行等价流程如下：

```bash
.venv/bin/python src/run_supplementary_retrieval.py
.venv/bin/python src/bootstrap_supplementary.py
.venv/bin/python src/analyze_controller_behavior.py
.venv/bin/python src/audit_supplementary.py

.venv/bin/python src/build_test_generation_sample.py
.venv/bin/python src/run_deduplicated_ollama_generation.py \
  --model qwen2.5:3b --num-ctx 8192 --num-predict 256 \
  --temperature 0 --seed 42
.venv/bin/python src/evaluate_test_generation.py
.venv/bin/python src/audit_test_generation.py
.venv/bin/python src/make_thesis_figures.py --overwrite
```

生成 JSONL 支持按 prompt hash 断点续跑；但不得把不同模型、prompt 或 decoding
设置追加到同一文件。最终验收要求：201 个对齐问题、804 个方法—问题记录、608
个 unique prompts、0 missing、0 API error、0 `done_reason=length`，且最大实际
prompt token 小于 8,192。正式数值和可辩护解释见
`docs/TEST_GENERATION_RESULTS.md`，图表说明见 `docs/FIGURE_GUIDE.md`。
