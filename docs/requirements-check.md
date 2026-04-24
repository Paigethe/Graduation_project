# BS/001 需求对照检查（静态核对）

日期：2026-02-06

## 0) 说明
- 核对范围：`01-毕业设计文档/开题报告1 - 副本.docx`、`01-毕业设计文档/任务书.docx`
- 核对方式：**静态核对**（仅检查代码与文档，不运行接口、不改动数据库）
- 结论类型：`done` / `partial` / `missing`

## 1) 需求来源与范围
- 开题报告：`01-毕业设计文档/开题报告1 - 副本.docx`
- 任务书：`01-毕业设计文档/任务书.docx`

## 2) 需求清单（编号 + 类别 + 指标）
> 需求按功能、算法/AI、性能、安全、测试、论文/附录划分。

| ID | 类别 | 需求/指标摘要 |
| --- | --- | --- |
| REQ-FUNC-01 | 功能 | 注册/登录/角色区分（学生/辅导员/学院管理员/系统管理员），JWT 身份校验 |
| REQ-FUNC-02 | 功能 | 心理知识库：分类、列表、阅读、收藏/取消收藏、学院定向推送 |
| REQ-FUNC-03 | 功能 | 问卷模板管理：题目/维度/权重可配置 |
| REQ-FUNC-04 | 功能 | 问卷发布与填写：学院/全校、有效期、提交与记录 |
| REQ-FUNC-05 | 功能 | 评估报告生成与查看：总分/维度/风险等级 |
| REQ-FUNC-06 | 功能 | 风险预警生成与确认/跟进 |
| REQ-FUNC-07 | 功能 | 干预建议创建、推送、状态跟进 |
| REQ-FUNC-08 | 功能 | AI 自助咨询 + 风险初筛 + 转人工提示/预警 |
| REQ-FUNC-09 | 功能 | 人工咨询实时交流 + 已读状态 + 加密存储 |
| REQ-FUNC-10 | 功能 | 学院看板/统计分析（风险分布、维度表现、趋势） |
| REQ-FUNC-11 | 功能 | 学院问卷结果查看（提交率、未提交名单、得分分布） |
| REQ-FUNC-12 | 功能 | 月度心理健康分析报告（导出 PDF） |
| REQ-FUNC-13 | 功能 | 学院数据备份/导出 |
| REQ-FUNC-14 | 功能 | 系统管理员运维监控、用户与权限、审计 |
| REQ-FUNC-15 | 功能 | 系统管理员全局全量备份 |
| REQ-ALG-01 | 算法/AI | 量表评估算法（SCL-90/SAS/SDS 等）权重优化 |
| REQ-ALG-02 | 算法/AI | 深度学习风险预测模型，准确率 >= 80% |
| REQ-ALG-03 | 算法/AI | 评估一致性 >= 90%（与专家评估） |
| REQ-ALG-04 | 算法/AI | AI 自助问答模型适配（24h） |
| REQ-ALG-05 | 算法/AI | 高风险关键词初筛 + 预警 + 转人工/通知教师 |
| REQ-PERF-01 | 性能 | 页面加载 <= 3s；问卷提交/评估生成 <= 5s |
| REQ-PERF-02 | 性能 | 支持 >= 1000 并发 |
| REQ-PERF-03 | 性能 | 72h 稳定运行，可用性 99.9% |
| REQ-SEC-01 | 安全 | 权限隔离：学生/教师/管理员仅访问授权数据 |
| REQ-SEC-02 | 安全 | 敏感数据加密、备份与访问控制 |
| REQ-TEST-01 | 测试 | 功能测试覆盖核心模块 |
| REQ-TEST-02 | 测试 | 性能测试与安全测试 |
| REQ-DOC-01 | 论文 | 正文包含：需求/架构/技术选型/算法/模块/测试结果 |
| REQ-DOC-02 | 附录 | 架构图、模块图、ER 图、伪代码、关键代码片段 |
| REQ-DOC-03 | 文献 | 参考文献 >= 15 篇，外文 >= 2 篇 |

## 3) 覆盖矩阵（现状 + 证据）
> 状态：done/partial/missing；证据为静态代码与文档路径。

| ID | 状态 | 证据 | 缺口说明 |
| --- | --- | --- | --- |
| REQ-FUNC-01 | done | `backend/apps/accounts/*`, `backend/psycare/urls.py`, `frontend/src/pages/AuthPage.vue`, `frontend/src/App.vue` | - |
| REQ-FUNC-02 | done | `backend/apps/knowledge/*`, `frontend/src/pages/KnowledgePage.vue`, `frontend/src/pages/CollegeAnalysisPage.vue` | - |
| REQ-FUNC-03 | done | `backend/apps/surveys/*`, `frontend/src/pages/SysAdminDatabasePage.vue` | - |
| REQ-FUNC-04 | done | `backend/apps/surveys/views.py`, `frontend/src/pages/SurveyPage.vue` | - |
| REQ-FUNC-05 | done | `backend/apps/assessments/*`, `frontend/src/pages/StudentReportPage.vue` | 算法深度见 REQ-ALG-* |
| REQ-FUNC-06 | done | `backend/apps/assessments/*`, `frontend/src/pages/CollegeDashboardPage.vue` | - |
| REQ-FUNC-07 | done | `backend/apps/interventions/*`, `frontend/src/pages/CounselorInterventionsPage.vue`, `frontend/src/pages/CollegeProgressPage.vue` | - |
| REQ-FUNC-08 | partial | `backend/apps/chat/utils.py`, `backend/apps/chat/views.py`, `frontend/src/pages/ChatPage.vue` | AI为规则回复；已支持自动转人工与提示 |
| REQ-FUNC-09 | partial | `backend/apps/chat/models.py`, `backend/apps/chat/views.py`, `frontend/src/pages/ChatPage.vue` | 已读回执与轮询已实现；实时延迟需验证 |
| REQ-FUNC-10 | done | `frontend/src/pages/CollegeDashboardPage.vue`, `frontend/src/pages/CollegeAnalysisPage.vue` | - |
| REQ-FUNC-11 | done | `backend/apps/surveys/views.py`(stats), `frontend/src/pages/CollegeAnalysisPage.vue` | - |
| REQ-FUNC-12 | done | `backend/apps/reports/views.py`, `frontend/src/pages/CollegeReportsPage.vue` | - |
| REQ-FUNC-13 | partial | `backend/apps/backups/views.py`, `backend/apps/backups/management/commands/backup_export.py`, `docs/backup.md` | 定时调度需运维落地 |
| REQ-FUNC-14 | done | `backend/apps/audit/*`, `frontend/src/pages/AdminMonitorDashboard.vue`, `frontend/src/pages/SysAdminUsersPage.vue`, `frontend/src/pages/SysAdminSecurityPage.vue` | - |
| REQ-FUNC-15 | done | `backend/apps/backups/views.py`, `frontend/src/pages/BackupPage.vue` | - |
| REQ-ALG-01 | partial | `backend/apps/assessments/services.py`, `backend/apps/surveys/management/commands/import_scale.py`, `docs/scales/README.md`, `docs/scripts/scale_csv_to_json.py`, `docs/scripts/generate_simulated_scales.py`, `docs/scales/scl90_simulated_full.json`, `docs/scales/sas_simulated_full.json`, `docs/scales/sds_simulated_full.json` | 已具备结构化模拟量表与导入管线；标准量表原题仍需授权后替换 |
| REQ-ALG-02 | partial | `backend/apps/assessments/predictor.py`, `backend/apps/assessments/services.py` | 模型接口占位，需替换为真实模型 |
| REQ-ALG-03 | partial | `docs/algorithm-evaluation.md`, `docs/algorithm-evaluation-template.csv`, `backend/apps/assessments/management/commands/evaluate_predictions.py`, `docs/algorithm-evaluation-baseline.json` | 缺专家评估数据与正式指标报告 |
| REQ-ALG-04 | partial | `backend/apps/chat/utils.py`, `backend/apps/chat/knowledge.py`, `backend/apps/chat/views.py`, `frontend/src/pages/ChatPage.vue` | 已接入 DeepSeek 模型调用与知识推荐，仍缺 RAG 引文追溯与效果评测 |
| REQ-ALG-05 | partial | `backend/apps/chat/views.py` | 已支持转人工；通知与流程需完善 |
| REQ-PERF-01 | partial | `docs/performance-test.md`, `docs/scripts/perf-quickcheck.sh` | 已有quickcheck基线，需补齐P95/压测结果 |
| REQ-PERF-02 | partial | `docs/performance-test.md`, `docs/scripts/locustfile.py` | 需补充并发测试结果 |
| REQ-PERF-03 | partial | `docs/performance-test.md` | 需补充72h稳定性结果 |
| REQ-SEC-01 | partial | `backend/apps/accounts/permissions.py`, `docs/security-test.md`, `docs/scripts/security-quickcheck.sh` | 已有quickcheck基线，需完整越权矩阵 |
| REQ-SEC-02 | partial | `backend/apps/chat/utils.py`, `backend/apps/backups/views.py` | 加密仅覆盖聊天消息；备份访问控制已加强 |
| REQ-TEST-01 | partial | `docs/curl-smoke-tests.md`, `docs/test-cases.md` | 仅用例与冒烟说明，缺执行记录 |
| REQ-TEST-02 | partial | `docs/performance-test.md`, `docs/security-test.md`, `docs/scripts/perf-quickcheck.sh`, `docs/scripts/security-quickcheck.sh` | 缺执行报告数据 |
| REQ-DOC-01 | partial | `docs/test-cases.md`, `docs/performance-test.md`, `docs/security-test.md`, `docs/algorithm-evaluation.md` | 正文仍需整理成论文结构 |
| REQ-DOC-02 | partial | `docs/scales/README.md`, `docs/backup.md` | 附录图表/ER/伪代码仍需补齐 |
| REQ-DOC-03 | missing | `01-毕业设计文档/任务书.docx` | 文献数量/外文占比需在论文中落实 |

## 4) 缺口分析（按类别汇总）
### 功能
- 核心闭环功能基本可跑通（问卷、评估、预警、干预、咨询、报表、备份）
- 人工咨询“准实时”已采用 1s 轮询，仍需补充延迟量化证据（日志/截图）
- 备份已有管理命令，生产环境定时调度（cron/systemd）仍需运维落地

### 算法/AI
- 量表模板已补充为结构化模拟版本（SCL-90/SAS/SDS），正式原题仍需授权替换
- 深度学习预测仍为占位推理（接口已预留），需接入真实模型并验证指标
- AI问答已接入 DeepSeek 模型，但缺少 RAG 引文追溯与量化评测结果

### 性能/安全/测试
- 已有 quickcheck 与脚本骨架，但缺 1000 并发、72h 稳定性和可用性正式报告
- 权限与安全测试已有基础用例，需补全完整角色-接口矩阵与执行证据
- 功能测试需要形成可追溯执行记录（时间、环境、结果、缺陷闭环）

### 论文/附录
- 论文正文与附录素材（架构图/ER图/伪代码/指标图）仍需整合为最终提交版

## 5) 风险与优先级说明（以功能完备/结果成熟为目标）
- **执行顺序**：核心闭环（登录→问卷→评估→预警→干预→咨询） → 学院管理（统计/报表/备份/进度） → 系统管理员（全局备份/审计核验） → 算法指标 → 测试结果（性能/安全/稳定性） → 论文/附录
- **P0（硬指标）**：REQ-ALG-02/03、REQ-PERF-01/02/03、REQ-SEC-01/02、REQ-FUNC-09（消息实时与已读）、REQ-FUNC-11（学院统计）、REQ-FUNC-08/REQ-ALG-05（AI高风险转人工）
- **P1（重要）**：REQ-FUNC-12（PDF报表）、REQ-FUNC-13/15（备份机制）、REQ-FUNC-10（趋势分析）、REQ-TEST-01/02、REQ-DOC-01/02/03
- **P2（优化）**：界面体验与可视化、额外数据指标扩展

## 6) 建议验收路径（可选）
> 仍以静态核对为主，以下为后续验收建议。
1. 走通核心业务闭环：登录 -> 知识 -> 问卷 -> 评估 -> 预警 -> 干预 -> 咨询 -> 备份（参考 `docs/curl-smoke-tests.md`）
2. 学院管理员视角：风险分布、问卷统计、干预进度、月度报表导出
3. 系统管理员视角：用户权限、审计日志、全局备份
4. 性能/安全：补齐测试脚本与结果报告
