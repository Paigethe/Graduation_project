# 前端页面与接口映射

前端目录：`02-系统实现代码/frontend/`（Vue3 + Vite + Element Plus + Tailwind，本地依赖，无 CDN）。

后端 API：`http://127.0.0.1:52517/api/`（Vite dev server 已代理 `/api`）。

## 角色菜单
- 学生：系统首页、心理知识库、在线测评、分析报告、AI 咨询、人工咨询
- 心理辅导员：辅导员工作台、学生档案管理、干预建议推送、咨询服务
- 二级学院管理员：学院看板、深度统计分析、干预进度监控、月度报表生成、学院数据备份
- 系统管理员：运维状态监控、用户与权限、操作日志审计、数据库管理、全局全量备份

## 页面与主要接口
### 学生端
- 系统首页：`GET /surveys/questionnaires/`、`GET /assessments/results/`、`GET /assessments/alerts/`、`GET /interventions/plans/`
- 心理知识库：`GET /knowledge/articles/`、`POST /knowledge/articles/{id}/favorite/`、`POST /knowledge/articles/{id}/unfavorite/`
- 在线测评：`GET /surveys/questionnaires/`、`POST /surveys/questionnaires/{id}/submit/`
- 分析报告：`GET /assessments/results/`、`GET /assessments/alerts/`
- AI 咨询：`POST /chat/conversations/ai/`（高风险会生成 RiskAlert）
- 人工咨询：`POST /chat/conversations/human/start/`、`GET/POST /chat/conversations/{id}/messages/`
- 人工咨询已读回执：`POST /chat/conversations/{id}/read/`

### 心理辅导员端
- 工作台：`GET /counselor/students/`、`GET /assessments/alerts/`、`GET /interventions/plans/`、`GET /chat/conversations/`
- 学生档案：`GET /counselor/students/`、`GET /students/{id}/profile/`、`POST /chat/conversations/human/start/`
- 干预建议：`GET /interventions/plans/`、`POST /interventions/plans/`、`PATCH /interventions/plans/{id}/`
- 咨询服务：`GET /chat/conversations/`、`GET/POST /chat/conversations/{id}/messages/`
- 咨询已读回执：`POST /chat/conversations/{id}/read/`

### 二级学院管理员端
- 学院看板：`GET /assessments/results/`、`GET /assessments/alerts/`、`GET /interventions/plans/`、`GET /surveys/questionnaires/`
- 深度统计分析：同上 + `GET /surveys/templates/`（用于发布问卷）+ `POST /surveys/questionnaires/` + `POST /knowledge/articles/`
- 问卷统计：`GET /surveys/questionnaires/{id}/stats/`（提交率/未提交名单/得分分布）
- 干预进度监控：`GET /interventions/plans/`、`GET /assessments/alerts/`
- 月度报表：`GET /reports/list/`、`POST /reports/monthly/`（支持 `format=pdf`） 、`GET /reports/download/?name=...`
- 学院数据备份：`POST /backups/export/`、`GET /backups/download/?name=...`

### 系统管理员端
- 运维状态监控：聚合调用 `GET /admin/users/`、`GET /colleges/`、`GET /assessments/results/`、`GET /assessments/alerts/`、`GET /admin/audit-logs/`
- 用户与权限：`GET/POST /admin/users/`、`GET/POST /admin/assignments/`、`GET /colleges/`
- 操作日志审计：`GET /admin/audit-logs/`
- 数据库管理：`GET/POST /surveys/templates/`、`GET/POST /surveys/questionnaires/`、`GET /colleges/`
- 全局全量备份：`POST /backups/export/`（按学院选择导出）
