# 算法评估记录（模板）

## 1) 评估目标
- 评估一致性 >= 90%
- 预测准确率 >= 80%

## 2) 数据说明
- 样本量：
- 来源：
- 标注方式：

## 3) 评估结果
| 指标 | 结果 | 通过/不通过 |
| --- | --- | --- |
| 评估一致性 |  |  |
| 预测准确率 |  |  |

## 4) 结论
- 说明：

## 5) 快速脚本
参考：`docs/scripts/evaluate_model.py`

### 输入样例
可参考 `docs/algorithm-evaluation-template.csv`，字段：
- `y_true`：专家/基准标签
- `y_pred`：模型预测标签

## 6) 基线评估（系统内一致性）
使用命令对 `risk_level` 与 `predicted_risk_level` 做一致性统计（非专家标签）：

```bash
conda run -n bs001-psycare python manage.py evaluate_predictions --out docs/algorithm-evaluation-baseline.json
```

基线结果（示例，非专家标签）：`docs/algorithm-evaluation-baseline.json`
