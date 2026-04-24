# Risk Model Baseline Experiment Report

- Generated at: `2026-02-24 18:13:10 UTC`
- Dataset summary: `/Users/xeanyu/Desktop/BS/001/04-risk-model-lab/outputs/dataset_summary.json`
- Run summary: `/Users/xeanyu/Desktop/BS/001/04-risk-model-lab/outputs/training_runs/run_summary.csv`

## Dataset Summary
- Total rows: `29102`
- Split sizes: train `20370`, val `4364`, test `4368`

### Label Distribution
| label | count | ratio |
| --- | --- | --- |
| high | 16323 | 56.09% |
| low | 11975 | 41.15% |
| medium | 804 | 2.76% |

### Source Composition
| source | rows_raw | rows_built | columns_raw |
| --- | --- | --- | --- |
| adil_student_depression | 27901 | 27901 | 18 |
| stress_monitoring | 1100 | 1100 | 21 |
| student_mental_health_small | 101 | 101 | 11 |

### Notes
- This unified dataset is intended for baseline risk classification.
- It is not longitudinal ground-truth for future 1-2 month risk prediction.

## Model Comparison
| run_name | model | val_macro_f1 | test_macro_f1 | test_accuracy | test_balanced_accuracy |
| --- | --- | --- | --- | --- | --- |
| mlp_20260224_180433 | mlp | 0.9825 | 0.9724 | 0.9934 | 0.9594 |
| rf_20260224_180305 | rf | 0.9744 | 0.9698 | 0.9940 | 0.9933 |
| logreg_20260224_180327 | logreg | 0.8568 | 0.8558 | 0.9588 | 0.9709 |
| logreg_20260224_180422 | logreg | 0.8574 | 0.8548 | 0.9586 | 0.9707 |

## Best Model
- Selected run: `mlp_20260224_180433`
- Model type: `mlp`
- Selection metric: `test_macro_f1` = `0.9724`
- Test accuracy: `0.9934`
- Test macro F1: `0.9724`
- Test balanced accuracy: `0.9594`

### Per-Class Test Metrics
| label | precision | recall | f1 | support |
| --- | --- | --- | --- | --- |
| low | 0.9933 | 0.9967 | 0.9950 | 1797 |
| medium | 0.9730 | 0.8852 | 0.9270 | 122 |
| high | 0.9943 | 0.9963 | 0.9953 | 2449 |

### Test Confusion Matrix
| actual \ predicted | low | medium | high |
| --- | --- | --- | --- |
| low | 1791 | 1 | 5 |
| medium | 5 | 108 | 9 |
| high | 7 | 2 | 2440 |

### Top Misclassifications
- `medium` -> `high`: `9` samples
- `high` -> `low`: `7` samples
- `low` -> `high`: `5` samples

## Limitations
- Public datasets are merged from different schemas and collection contexts.
- Labels are partly rule-derived proxies, not clinically verified longitudinal outcomes.
- This baseline validates engineering feasibility; it does not prove 1-2 month future-risk prediction in production.
