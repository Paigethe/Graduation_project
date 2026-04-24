# 虚拟数据（Seed）

为便于快速演示“登录→问卷→评估→预警→干预→咨询→报表/备份”全链路，后端提供可重复执行的初始化命令。

## 初始化命令
在 `02-系统实现代码/backend/` 下执行：

```bash
conda run -n bs001-psycare python manage.py seed_demo
```

可选参数（生成更多模拟数据）：

```bash
conda run -n bs001-psycare python manage.py seed_demo \
  --students-per-college 30 \
  --counselors-per-college 3 \
  --responses-per-questionnaire 20 \
  --history-days 120
```

参数说明：
- `--students-per-college`：每个学院额外生成学生数（默认 20）
- `--counselors-per-college`：每个学院生成咨询教师数（默认 2）
- `--responses-per-questionnaire`：每份问卷生成作答样本上限（默认 12）
- `--history-days`：模拟数据在最近 N 天内分布（默认 90）

## 包含内容（摘要）
- 学院：4个学院（计算机、外国语、机械工程、经济管理）
- 账号：系统管理员 / 学院管理员 / 咨询教师 / 学生（默认口令 `123456`）
- 量表模板：
  - `SCL-90 示例（10题）`
  - `SCL-90 结构化模拟量表（90题）`
  - `SAS 结构化模拟量表（20题）`
  - `SDS 结构化模拟量表（20题）`
- 问卷：按学院自动生成多份筛查问卷 + 全校问卷
- 作答与评估：自动生成问卷作答、风险评估、风险预警（按低/中/高风险分布）
- 干预：中高风险样本自动生成干预计划
- 咨询：自动生成部分 AI/人工咨询会话与消息样本
- 知识库：分类文章 + 学院定向文章

> 注意：量表题目与选项内容使用“示例版/模拟文案”，避免引入受版权限制的原题文本；业务流程与评分/风险分级逻辑可完整跑通。
> 如需导入标准量表，请使用 `docs/scales/README.md` 中的导入命令。

## 默认账号（保留）
- 系统管理员：`admin / 123456`
- 二级学院管理员：`college_admin / 123456`（计算机学院）
- 咨询教师：`counselor1 / 123456`（计算机学院）
- 学生：`student1 / 123456`（计算机学院）
- 学生：`student2 / 123456`（计算机学院）

## 默认分配关系
- `counselor1` 已分配给 `student1`、`student2`
- 其余生成学生按学院在咨询教师之间轮询分配
