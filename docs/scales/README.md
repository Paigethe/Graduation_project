# 量表模板导入

## 一、直接导入 JSON

```bash
conda run -n bs001-psycare python manage.py import_scale --file docs/scales/scale-template.example.json --update
```

## 二、CSV 转 JSON 再导入

1) 用 `docs/scales/scl90_template.csv` 填写标准题干与权重

2) 转换为 JSON：

```bash
python docs/scripts/scale_csv_to_json.py \
  docs/scales/scl90_template.csv \
  docs/scales/scl90_template.json \
  --name "SCL-90 标准量表" \
  --scale_type scl90_sample \
  --desc "标准量表题干与权重"
```

3) 导入模板：

```bash
conda run -n bs001-psycare python manage.py import_scale --file docs/scales/scl90_template.json --update
```

## 三、快速生成结构化模拟量表（推荐联调）

> 说明：以下为**非版权原题**的结构化模拟题库，用于接口联调、流程演示、模型调用接口验证。

1) 生成模拟模板：

```bash
python docs/scripts/generate_simulated_scales.py
```

生成文件：
- `docs/scales/scl90_simulated_full.json`（90题）
- `docs/scales/sas_simulated_full.json`（20题）
- `docs/scales/sds_simulated_full.json`（20题）

2) 依次导入：

```bash
conda run -n bs001-psycare python manage.py import_scale --file docs/scales/scl90_simulated_full.json --update
conda run -n bs001-psycare python manage.py import_scale --file docs/scales/sas_simulated_full.json --update
conda run -n bs001-psycare python manage.py import_scale --file docs/scales/sds_simulated_full.json --update
```

## 备注
- 示例/模拟模板用于开发与测试，不等同于正式量表原文。
- 如需论文中声明“标准量表”，请自行处理题干来源与授权合规。
