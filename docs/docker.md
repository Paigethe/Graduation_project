# Docker（MySQL / Redis）

本项目仅使用 Docker 启动 **MySQL** 与 **Redis**，避免影响你电脑上已有容器。

## 启动
在 `02-系统实现代码/` 下执行：

```bash
cp .env.example .env
docker compose up -d
```

## 停止
```bash
docker compose down
```

## 彻底重建（会删除数据库数据）
```bash
docker compose down -v
docker compose up -d
```

## 数据库字符集（重要）
- 服务器与数据库：`utf8mb4`
- 排序规则：`utf8mb4_unicode_ci`

项目会在容器初始化时强制设置，避免中文入库/取出后乱码。
