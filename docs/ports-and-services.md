# 端口与服务

本项目要求使用五位数端口；基准端口随机取值：`52517`。

## 本机端口（Host）
- 前端（Vite）：`52516`
- 后端（Django API）：`52517`
- MySQL（Docker）：`52518` → 容器内 `3306`
- Redis（Docker）：`52519` → 容器内 `6379`

## 服务与容器命名
- MySQL：`bs001_psycare_mysql`
- Redis：`bs001_psycare_redis`

