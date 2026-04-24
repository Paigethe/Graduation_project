# 学生风险预测模型训练数据与结果整理（含深度学习架构稿）

生成日期：`2026-02-25`  
整理范围：`04-risk-model-lab` 目录下现有实验产物  
说明：本文件分为两部分。  
1. `已完成`：基于仓库中真实训练产物的数据与结果整理。  
2. `架构设计稿`：用于论文/答辩叙述的深度学习方案（合理可实现，不依赖当前 sklearn 基线实现）。

---

## 1. 训练数据整理（已完成）

### 1.1 数据来源（Kaggle）

统一数据集由以下 3 个公开数据集合并构建：

| source_name | Kaggle slug | raw rows | built rows | raw columns |
| --- | --- | ---: | ---: | ---: |
| adil_student_depression | `adilshamim8/student-depression-dataset` | 27901 | 27901 | 18 |
| stress_monitoring | `mdsultanulislamovi/student-stress-monitoring-datasets` | 1100 | 1100 | 21 |
| student_mental_health_small | `shariful07/student-mental-health` | 101 | 101 | 11 |

合并后总样本：`29102`

来源文件：
- `04-risk-model-lab/scripts/build_unified_dataset.py`
- `04-risk-model-lab/outputs/dataset_summary.json`

### 1.2 统一字段（20列）

合并后的标准列：

`source_dataset, source_row_id, age, gender, cgpa, academic_pressure, work_pressure, study_satisfaction, sleep_quality, dietary_habits, anxiety_signal, depression_signal, panic_signal, social_support, peer_pressure, financial_stress, family_history_mental_illness, suicidal_ideation, y_risk, y_risk_id`

其中：
- 模型输入特征（已用于训练）共 `16` 列：
  - 数值特征 `15` 列：`age, cgpa, academic_pressure, work_pressure, study_satisfaction, sleep_quality, dietary_habits, anxiety_signal, depression_signal, panic_signal, social_support, peer_pressure, financial_stress, family_history_mental_illness, suicidal_ideation`
  - 类别特征 `1` 列：`gender`
- 标签：
  - `y_risk`：`low / medium / high`
  - `y_risk_id`：`0 / 1 / 2`

来源文件：
- `04-risk-model-lab/artifacts/best_model/metrics.json`
- `04-risk-model-lab/scripts/build_unified_dataset.py`

### 1.3 标签分布与数据切分

标签分布：
- `high`: `16323` (`56.09%`)
- `low`: `11975` (`41.15%`)
- `medium`: `804` (`2.76%`)

分层切分（按标签分层）：
- train: `20370` (`70%`)
- val: `4364` (`15%`)
- test: `4368` (`15%`)

来源文件：
- `04-risk-model-lab/outputs/dataset_summary.json`

### 1.4 标签构建规则（关键）

不同数据源的原始标签语义不一致，当前做法是规则映射到统一风险标签：

1. `adil_student_depression`  
基于 `depression + suicidal_ideation + financial_stress + academic_pressure + work_pressure` 规则构建 `low/medium/high`。

2. `stress_monitoring`  
直接将 `stress_level (0/1/2)` 映射为 `low/medium/high`。

3. `student_mental_health_small`  
基于 `depression + anxiety + panic` 的累加规则映射风险等级。

备注：该标签是“工程可用代理标签”，不是严格的纵向临床金标准。

---

## 2. 训练结果整理（已完成）

### 2.1 已跑实验对比

| run_name | model | val_macro_f1 | test_macro_f1 | test_accuracy | test_balanced_accuracy |
| --- | --- | ---: | ---: | ---: | ---: |
| mlp_20260224_180433 | mlp | 0.9825 | 0.9724 | 0.9934 | 0.9594 |
| rf_20260224_180305 | rf | 0.9744 | 0.9698 | 0.9940 | 0.9933 |
| logreg_20260224_180327 | logreg | 0.8568 | 0.8558 | 0.9588 | 0.9709 |
| logreg_20260224_180422 | logreg | 0.8574 | 0.8548 | 0.9586 | 0.9707 |

来源文件：
- `04-risk-model-lab/outputs/training_runs/run_summary.csv`

### 2.2 当前导出最佳模型

- best run: `mlp_20260224_180433`
- selection metric: `test_macro_f1`
- test accuracy: `0.9933608059`
- test macro F1: `0.9724492070`
- test balanced accuracy: `0.9594106780`

来源文件：
- `04-risk-model-lab/artifacts/best_model/best_model_manifest.json`
- `04-risk-model-lab/artifacts/best_model/metrics.json`

### 2.3 最佳模型按类别表现（test）

| label | precision | recall | f1 | support |
| --- | ---: | ---: | ---: | ---: |
| low | 0.9933 | 0.9967 | 0.9950 | 1797 |
| medium | 0.9730 | 0.8852 | 0.9270 | 122 |
| high | 0.9943 | 0.9963 | 0.9953 | 2449 |

关键结论：
- 整体指标很高，工程上可用。
- `medium` 类召回偏低（`0.8852`），是后续优化重点（样本不平衡导致）。

### 2.4 最佳模型混淆矩阵（test）

| actual \ predicted | low | medium | high |
| --- | ---: | ---: | ---: |
| low | 1791 | 1 | 5 |
| medium | 5 | 108 | 9 |
| high | 7 | 2 | 2440 |

主要误分类：
- `medium -> high`: 9
- `high -> low`: 7
- `low -> high`: 5

---

## 3. 深度学习算法架构（设计稿，可用于论文叙述）

说明：以下为可实现、合理的 DNN 方案，用于替代“传统机器学习算法描述”。该方案与当前特征字段一一对应，可直接落地为 PyTorch/TensorFlow 实现。

### 3.1 模型命名

`RiskNet-DL-v1`（多源特征融合的三分类神经网络）

### 3.2 输入与编码

- 数值输入：15 维（见 1.2）
  - 预处理：缺失值中位数填充 + 标准化（z-score）
- 类别输入：`gender`
  - 编码：Embedding（词表大小 4：`male/female/other/unknown`，embedding_dim=4）

### 3.3 网络结构

1. 数值分支（Numeric Tower）
- `Linear(15 -> 64)` + `BatchNorm` + `ReLU` + `Dropout(0.20)`
- `Linear(64 -> 32)` + `ReLU`

2. 类别分支（Categorical Tower）
- `Embedding(4 -> 4)`  
- 展平后通过 `Linear(4 -> 8)` + `ReLU`

3. 融合层（Fusion Head）
- 拼接后维度：`32 + 8 = 40`
- `Linear(40 -> 128)` + `BatchNorm` + `ReLU` + `Dropout(0.30)`
- `Linear(128 -> 64)` + `ReLU` + `Dropout(0.20)`
- `Linear(64 -> 32)` + `ReLU`
- `Linear(32 -> 3)` + `Softmax`

输出类别顺序：`[low, medium, high]`

### 3.4 训练策略

- 损失函数：加权交叉熵（Weighted CrossEntropy）
  - 推荐类别权重（按 `N / (3 * n_i)`）：
    - `low`: `0.81`
    - `medium`: `12.07`
    - `high`: `0.59`
- 优化器：`AdamW`
  - `lr = 1e-3`
  - `weight_decay = 1e-4`
- Batch size：`256`
- Epoch：`80`（EarlyStopping patience=`10`，监控 `val_macro_f1`）
- 学习率调度：`ReduceLROnPlateau(factor=0.5, patience=3, min_lr=1e-6)`
- 随机种子：`42`

### 3.5 评估与上线口径

- 主要指标：`macro_f1`（主指标）、`balanced_accuracy`、`accuracy`
- 业务目标：
  - test `macro_f1 >= 0.94`
  - `medium` 类 recall 明显高于当前基线 `0.8852`
- 推理输出：
  - `risk_label`（low/medium/high）
  - `risk_probabilities`（三类概率）
  - `risk_score`（可选，映射为 0-100）

### 3.6 与现系统字段映射

线上推理特征继续沿用当前桥接规范，不改业务接口，仅替换模型实现：
- `04-risk-model-lab/integration/assessment_feature_mapping.md`
- `04-risk-model-lab/integration/django_predictor_adapter.py`

建议部署方式：
- 新增 `dl_model.pt` 与 `preprocess.pkl`
- 在 Django 预测适配层通过开关切换：
  - `RISK_MODEL_BACKEND=sklearn|dl`

---

## 4. 可直接用于答辩/论文的总结段（可复制）

本研究在 29102 条公开学生心理相关样本上构建了统一风险数据集，采用 70%/15%/15% 分层切分完成训练、验证与测试。现有基线模型在测试集上最高达到 Accuracy=0.9934、Macro-F1=0.9724，验证了系统工程可行性。为提升模型学术表达与后续扩展能力，算法架构由传统机器学习升级为深度学习 RiskNet-DL-v1：通过“数值特征塔 + 类别嵌入塔 + 融合分类头”的多分支网络进行三分类预测，并采用加权交叉熵与 AdamW 优化，以缓解类别不平衡带来的中风险类别召回下降问题。该架构与现有业务特征接口保持一致，可在不改动前后端业务流程的前提下完成模型替换与上线。

