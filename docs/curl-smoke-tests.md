# curl 打通业务逻辑（冒烟测试）

目标：用 `curl` 将核心业务逻辑跑通（注册/登录→知识→问卷→评估→干预→咨询→备份）。

前置条件：
- 后端已运行：`http://127.0.0.1:52517`
- 已初始化虚拟数据：`conda run -n bs001-psycare python manage.py seed_demo`

## 0) 基础变量
```bash
export API="http://127.0.0.1:52517/api"
```

健康检查：
```bash
curl -s "$API/health/" | jq
```

## 1) 学生登录 + 个人信息
```bash
export TOKEN_STUDENT1=$(curl -s "$API/auth/token/" \\
  -H 'Content-Type: application/json' \\
  -d '{\"username\":\"student1\",\"password\":\"123456\"}' | jq -r .access)

curl -s "$API/auth/me/" -H "Authorization: Bearer $TOKEN_STUDENT1" | jq
```

## 2) 知识模块：列表 + 收藏/取消收藏
```bash
curl -s "$API/knowledge/articles/" -H "Authorization: Bearer $TOKEN_STUDENT1" | jq

export ARTICLE_ID=$(curl -s "$API/knowledge/articles/" -H "Authorization: Bearer $TOKEN_STUDENT1" | jq -r '.results[0].id')
curl -s -X POST "$API/knowledge/articles/$ARTICLE_ID/favorite/" -H "Authorization: Bearer $TOKEN_STUDENT1" | jq
curl -s -X POST "$API/knowledge/articles/$ARTICLE_ID/unfavorite/" -H "Authorization: Bearer $TOKEN_STUDENT1" | jq
```

## 3) 问卷：列表 + 提交
```bash
curl -s "$API/surveys/questionnaires/" -H "Authorization: Bearer $TOKEN_STUDENT1" | jq

export Q_ID=$(curl -s "$API/surveys/questionnaires/" -H "Authorization: Bearer $TOKEN_STUDENT1" | jq -r '.results[0].id')

curl -s -X POST "$API/surveys/questionnaires/$Q_ID/submit/" \\
  -H "Authorization: Bearer $TOKEN_STUDENT1" \\
  -H 'Content-Type: application/json' \\
  -d '{\"answers\":{\"1\":4,\"2\":4,\"3\":3,\"4\":3,\"5\":4,\"6\":4,\"7\":3,\"8\":3,\"9\":2,\"10\":2}}' | jq
```

## 4) 评估结果 + 风险预警（学生视角）
```bash
curl -s "$API/assessments/results/" -H "Authorization: Bearer $TOKEN_STUDENT1" | jq
curl -s "$API/assessments/alerts/" -H "Authorization: Bearer $TOKEN_STUDENT1" | jq
```

## 5) 咨询教师：查看预警 + 创建干预建议
```bash
export TOKEN_COUNSELOR=$(curl -s "$API/auth/token/" \\
  -H 'Content-Type: application/json' \\
  -d '{\"username\":\"counselor1\",\"password\":\"123456\"}' | jq -r .access)

curl -s "$API/assessments/alerts/" -H "Authorization: Bearer $TOKEN_COUNSELOR" | jq

export STUDENT1_ID=$(curl -s "$API/auth/me/" -H "Authorization: Bearer $TOKEN_STUDENT1" | jq -r .id)
curl -s -X POST "$API/interventions/plans/" \\
  -H "Authorization: Bearer $TOKEN_COUNSELOR" \\
  -H 'Content-Type: application/json' \\
  -d '{\"student_id\":'"$STUDENT1_ID"',\"title\":\"干预建议（示例）\",\"content\":\"建议：规律作息 + 每日10分钟放松训练；必要时预约面谈。\",\"status\":\"sent\"}' | jq
```

## 6) 人工咨询：创建会话 + 发消息
学生创建人工会话（自动选择已分配教师）：
```bash
export CONV=$(curl -s -X POST "$API/chat/conversations/human/start/" \\
  -H "Authorization: Bearer $TOKEN_STUDENT1" \\
  -H 'Content-Type: application/json' \\
  -d '{}' )
export CONV_ID=$(echo "$CONV" | jq -r .id)
echo "$CONV" | jq

curl -s -X POST "$API/chat/conversations/$CONV_ID/messages/" \\
  -H "Authorization: Bearer $TOKEN_STUDENT1" \\
  -H 'Content-Type: application/json' \\
  -d '{\"content\":\"老师您好，我最近压力有点大。\"}' | jq

curl -s "$API/chat/conversations/$CONV_ID/messages/" -H "Authorization: Bearer $TOKEN_COUNSELOR" | jq

# 已读回执（咨询教师标记已读）
curl -s -X POST "$API/chat/conversations/$CONV_ID/read/" \\
  -H "Authorization: Bearer $TOKEN_COUNSELOR" | jq
```

## 7) AI 自助：对话 + 高风险关键词预警
```bash
curl -s -X POST "$API/chat/conversations/ai/" \\
  -H "Authorization: Bearer $TOKEN_STUDENT1" \\
  -H 'Content-Type: application/json' \\
  -d '{\"content\":\"我最近有点焦虑，睡不好。\"}' | jq

# 高风险示例（会生成 RiskAlert）
curl -s -X POST "$API/chat/conversations/ai/" \\
  -H "Authorization: Bearer $TOKEN_STUDENT1" \\
  -H 'Content-Type: application/json' \\
  -d '{\"content\":\"我不想活了\"}' | jq

# 关注输出字段：
# - handoff_required: 是否触发自动转人工
# - handoff_conversation: 自动创建的人工会话（如已分配教师）
# - handoff_error: 未分配教师时的提示
```

## 8) 二级学院管理员：导出备份
```bash
export TOKEN_COLLEGE_ADMIN=$(curl -s "$API/auth/token/" \\
  -H 'Content-Type: application/json' \\
  -d '{\"username\":\"college_admin\",\"password\":\"123456\"}' | jq -r .access)

curl -s -X POST "$API/backups/export/" \\
  -H "Authorization: Bearer $TOKEN_COLLEGE_ADMIN" \\
  -H 'Content-Type: application/json' \\
  -d '{}' | jq
```

## 9) 二级学院管理员：生成月度报表 + 下载
```bash
curl -s -X POST "$API/reports/monthly/" \\
  -H "Authorization: Bearer $TOKEN_COLLEGE_ADMIN" \\
  -H 'Content-Type: application/json' \\
  -d '{\"month\":\"2026-02\",\"metrics\":[\"风险分布\",\"干预效果\"],\"format\":\"pdf\"}' | jq

curl -s "$API/reports/list/" -H "Authorization: Bearer $TOKEN_COLLEGE_ADMIN" | jq

export REPORT_NAME=$(curl -s "$API/reports/list/" -H "Authorization: Bearer $TOKEN_COLLEGE_ADMIN" | jq -r '.results[0].name')
curl -s -L "$API/reports/download/?name=$REPORT_NAME" -H "Authorization: Bearer $TOKEN_COLLEGE_ADMIN" | jq
```

## 10) 系统管理员：查看审计日志
```bash
export TOKEN_ADMIN=$(curl -s "$API/auth/token/" \\
  -H 'Content-Type: application/json' \\
  -d '{\"username\":\"admin\",\"password\":\"123456\"}' | jq -r .access)

curl -s "$API/admin/audit-logs/" -H "Authorization: Bearer $TOKEN_ADMIN" | jq
```
